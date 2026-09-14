"""Generación automática de asientos contables (partida doble).

Replica los asientos que el VFP producía en `cb-crasientootorga` (otorgamiento)
y en la cobranza. Todo asiento queda balanceado (Σ debe = Σ haber).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app import models

CERO = Decimal("0.00")

# Plan de cuentas mínimo (código, nombre, tipo).
PLAN_CUENTAS = [
    ("1.1.01", "Caja", "activo"),
    ("1.1.02", "Banco", "activo"),
    ("1.2.01", "Créditos a cobrar", "activo"),
    ("2.1.01", "IVA débito fiscal", "pasivo"),
    ("4.1.01", "Intereses ganados", "ingreso"),
    ("4.1.02", "Intereses punitorios ganados", "ingreso"),
    ("4.1.03", "Seguros", "ingreso"),
    ("4.1.04", "Gastos administrativos", "ingreso"),
]
_NOMBRE = {c: n for c, n, _ in PLAN_CUENTAS}


def seed_plan_cuentas(db: Session) -> None:
    if db.scalar(select(models.CuentaContable).limit(1)):
        return
    for cod, nom, tipo in PLAN_CUENTAS:
        db.add(models.CuentaContable(codigo=cod, nombre=nom, tipo=tipo))


def _linea(cod: str, debe=CERO, haber=CERO) -> models.AsientoLinea:
    return models.AsientoLinea(cuenta_codigo=cod, cuenta_nombre=_NOMBRE[cod],
                               debe=debe, haber=haber)


def asiento_otorgamiento(db: Session, credito: models.Credito) -> models.Asiento:
    """Debe Créditos a cobrar / Haber Caja, por el capital otorgado."""
    a = models.Asiento(
        fecha=credito.fecha_otorgamiento or date.today(),
        concepto=f"Otorgamiento crédito N° {credito.id}",
        origen="otorgamiento", ref_id=credito.id,
        lineas=[
            _linea("1.2.01", debe=credito.capital),
            _linea("1.1.01", haber=credito.capital),
        ],
    )
    db.add(a)
    return a


def asiento_cobranza(db: Session, recibo: models.Recibo) -> models.Asiento:
    """Debe Caja (total) / Haber capital, intereses, punitorios, seguros, gastos, IVA."""
    pagos = db.scalars(select(models.PagoCuota).where(
        models.PagoCuota.recibo_id == recibo.id)).all()
    cap = sum((p.capital for p in pagos), CERO)
    interes = sum((p.interes for p in pagos), CERO)
    pun = sum((p.interes_punitorio for p in pagos), CERO)
    seg = sum((p.seguro for p in pagos), CERO)
    gas = sum((p.gastos_adm for p in pagos), CERO)
    # todo el IVA (interés, seguro, gastos y punitorios) como residual → balancea
    iva = recibo.total - (cap + interes + pun + seg + gas)

    lineas = [_linea("1.1.01", debe=recibo.total)]
    for cod, monto in [("1.2.01", cap), ("4.1.01", interes), ("4.1.02", pun),
                       ("4.1.03", seg), ("4.1.04", gas), ("2.1.01", iva)]:
        if monto and monto != CERO:
            lineas.append(_linea(cod, haber=monto))

    a = models.Asiento(
        fecha=recibo.fecha_pago,
        concepto=f"Cobranza recibo N° {recibo.numero}",
        origen="cobranza", ref_id=recibo.id, lineas=lineas,
    )
    db.add(a)
    return a


# ---------------- asientos de contratos pp (Configurar Créditos) ----------------
# Nombres de cuentas usadas por el mapeo contable del componente ACCOUNTING.
CUENTAS_PP_NOMBRE = {
    "1.1.01": "Caja", "1.1.02": "Banco", "1.2.01": "Créditos a cobrar",
    "1.2.02": "Intereses a devengar", "1.1.05.01": "Préstamos otorgados",
    "4.1.01": "Intereses ganados", "4.1.02": "Intereses punitorios ganados",
    "4.1.04": "Gastos administrativos", "2.1.01": "IVA débito fiscal", "2.1.07": "IVA débito fiscal",
}
CAJA_PP = "1.1.01"
INT_A_DEVENGAR = "1.2.02"  # activo: intereses devengados pendientes de cobro


def _nom_pp(cod: str) -> str:
    return CUENTAS_PP_NOMBRE.get(cod, cod)


def _lpp(cod: str, debe=CERO, haber=CERO) -> models.AsientoLinea:
    return models.AsientoLinea(cuenta_codigo=cod, cuenta_nombre=_nom_pp(cod), debe=debe, haber=haber)


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or 0))


def asiento_pp_otorgamiento(db: Session, contrato) -> models.Asiento:
    """Debe cuenta de capital / Haber Caja, por el capital desembolsado."""
    ct = (contrato.snapshot_producto or {}).get("contabilidad", {})
    cap = ct.get("cuentaCapital") or "1.2.01"
    monto = _dec(contrato.monto_original)
    a = models.Asiento(fecha=contrato.fecha_valor, origen="pp_otorgamiento", ref_id=None,
                       concepto=f"Otorgamiento contrato {contrato.numero_contrato}",
                       lineas=[_lpp(cap, debe=monto), _lpp(CAJA_PP, haber=monto)])
    db.add(a); db.flush()
    return a


def asiento_pp_devengo(db: Session, contrato, interes: Decimal, fecha, concepto) -> models.Asiento:
    """Devengamiento: Debe Intereses a devengar (activo) / Haber Intereses ganados (ingreso)."""
    ct = (contrato.snapshot_producto or {}).get("contabilidad", {})
    intc = ct.get("cuentaInteres") or "4.1.01"
    monto = _dec(interes)
    a = models.Asiento(fecha=fecha, origen="pp_devengo", ref_id=None, concepto=concepto,
                       lineas=[_lpp(INT_A_DEVENGAR, debe=monto), _lpp(intc, haber=monto)])
    db.add(a); db.flush()
    return a


def asiento_pp_pago(db: Session, contrato, cuota, fecha, concepto,
                    int_punitorio: Decimal = CERO, iva_punitorio: Decimal = CERO,
                    monto: Decimal | None = None) -> models.Asiento:
    """Debe Caja / Haber capital, interés, comisiones, impuestos y punitorios (separados).

    - El interés, si la cuota ya fue devengada, se acredita a Intereses a devengar (salda la
      cuenta a cobrar) en vez de a Intereses ganados, para no reconocer el ingreso dos veces.
    - Las comisiones (cargos de otorgamiento/administrativos) van a la cuenta de comisiones y
      los impuestos (IVA/sellado) a la cuenta de impuestos — NO se mezclan.
    - El interés punitorio (mora) va a 4.1.02 y su IVA a la cuenta de impuestos.
    - `monto`: si se paga menos que el total de la cuota (pago parcial), las porciones
      capital/interés/comisiones/impuestos se imputan **proporcionalmente**.
    """
    ct = (contrato.snapshot_producto or {}).get("contabilidad", {})
    cap = ct.get("cuentaCapital") or "1.2.01"
    intc = INT_A_DEVENGAR if getattr(cuota, "devengada", False) else (ct.get("cuentaInteres") or "4.1.01")
    comisc = ct.get("cuentaComision") or "4.1.04"
    ivac = ct.get("cuentaIva") or "2.1.01"
    int_pun, iva_pun = _dec(int_punitorio), _dec(iva_punitorio)
    total, capital, interes = _dec(cuota.total), _dec(cuota.capital), _dec(cuota.interes)
    impuestos = _dec(getattr(cuota, "impuestos", 0))
    comisiones = total - capital - interes - impuestos  # cargos netos de impuestos
    pagado = _dec(monto) if monto is not None else total
    if total > CERO and pagado < total:                  # pago parcial: imputación proporcional
        f = pagado / total
        capital = (capital * f).quantize(Decimal("0.01"))
        interes = (interes * f).quantize(Decimal("0.01"))
        impuestos = (impuestos * f).quantize(Decimal("0.01"))
        comisiones = pagado - capital - interes - impuestos   # el resto, para que cierre exacto
        total = pagado
    caja = total + int_pun + iva_pun                     # el cliente paga cuota (o parcial) + mora
    lineas = [_lpp(CAJA_PP, debe=caja)]
    for cod, monto in [(cap, capital), (intc, interes), (comisc, comisiones),
                       ("4.1.02", int_pun), (ivac, impuestos + iva_pun)]:
        if monto and monto != CERO:
            lineas.append(_lpp(cod, haber=monto))
    a = models.Asiento(fecha=fecha, origen="pp_cobranza", ref_id=None, concepto=concepto, lineas=lineas)
    db.add(a); db.flush()
    return a


def asiento_pp_payoff(db: Session, contrato, saldo, fecha, concepto) -> models.Asiento:
    """Debe Caja / Haber cuenta de capital, por el capital cancelado."""
    ct = (contrato.snapshot_producto or {}).get("contabilidad", {})
    cap = ct.get("cuentaCapital") or "1.2.01"
    monto = _dec(saldo)
    a = models.Asiento(fecha=fecha, origen="pp_cobranza", ref_id=None, concepto=concepto,
                       lineas=[_lpp(CAJA_PP, debe=monto), _lpp(cap, haber=monto)])
    db.add(a); db.flush()
    return a


def asiento_pp_reversa(db: Session, original: models.Asiento, fecha) -> models.Asiento:
    """Contra-asiento: invierte debe/haber del asiento original (no lo borra)."""
    lineas = [_lpp(l.cuenta_codigo, debe=_dec(l.haber), haber=_dec(l.debe)) for l in original.lineas]
    a = models.Asiento(fecha=fecha, origen="pp_reversa", ref_id=None,
                       concepto=f"Reversa asiento N° {original.id} — {original.concepto}", lineas=lineas)
    db.add(a); db.flush()
    return a


def balanceado(asiento: models.Asiento) -> bool:
    debe = sum((l.debe for l in asiento.lineas), CERO)
    haber = sum((l.haber for l in asiento.lineas), CERO)
    return debe == haber


def balance_sumas_saldos(db: Session, desde=None, hasta=None) -> dict:
    """Balance de sumas y saldos de la contabilidad de la APP (doble partida): por cuenta, total
    debe/haber y saldo deudor/acreedor. Cuadra por diseño (sumas iguales, saldos iguales).
    Excluye el mayor plano legacy migrado de VFP (origen='legacy', de una sola pierna) — ese se
    consulta en el Mayor. Filtrar la app deja el balance cuadrado e instantáneo (H-113)."""
    L = models.AsientoLinea
    q = (select(L.cuenta_codigo, L.cuenta_nombre,
                func.coalesce(func.sum(L.debe), 0), func.coalesce(func.sum(L.haber), 0))
         .join(models.Asiento, models.Asiento.id == L.asiento_id)
         .where(models.Asiento.origen != "legacy")   # sólo contabilidad de la app
         .group_by(L.cuenta_codigo, L.cuenta_nombre)
         .order_by(L.cuenta_codigo))
    if desde:
        q = q.where(models.Asiento.fecha >= desde)
    if hasta:
        q = q.where(models.Asiento.fecha <= hasta)

    filas = []
    tot = {"debe": CERO, "haber": CERO, "deudor": CERO, "acreedor": CERO}
    for cod, nom, debe, haber in db.execute(q).all():
        debe, haber = Decimal(debe), Decimal(haber)
        saldo = debe - haber
        deudor = saldo if saldo > 0 else CERO
        acreedor = -saldo if saldo < 0 else CERO
        filas.append({"cuenta_codigo": cod, "cuenta_nombre": nom,
                      "debe": debe, "haber": haber,
                      "saldo_deudor": deudor, "saldo_acreedor": acreedor})
        tot["debe"] += debe; tot["haber"] += haber
        tot["deudor"] += deudor; tot["acreedor"] += acreedor
    return {"cuentas": filas, "total": tot,
            "cuadra": tot["debe"] == tot["haber"] and tot["deudor"] == tot["acreedor"]}


def iva_periodo(db: Session, desde, hasta) -> dict:
    """IVA débito fiscal (a pagar) del período, a partir de los asientos.

    Informe VFP: cb-iva-a-pagar-periodo. Suma la cuenta 2.1.01 (IVA débito)
    de los asientos de cobranza dentro del rango de fechas.
    """
    q = (
        select(func.coalesce(func.sum(models.AsientoLinea.haber), 0),
               func.count(func.distinct(models.Asiento.id)))
        .join(models.Asiento, models.Asiento.id == models.AsientoLinea.asiento_id)
        .where(models.AsientoLinea.cuenta_codigo == "2.1.01",
               models.Asiento.fecha >= desde, models.Asiento.fecha <= hasta)
    )
    iva, n = db.execute(q).one()
    return {"desde": desde, "hasta": hasta,
            "iva_debito": Decimal(iva), "cantidad_asientos": n}


def iva_egresos(db: Session, desde, hasta) -> dict:
    """IVA de egresos de créditos (VFP: cb-egivaegresos) — desbloqueado por H-011."""
    q = (select(func.coalesce(func.sum(models.OrdenPago.iva), 0),
                func.count(models.OrdenPago.id))
         .where(models.OrdenPago.fecha >= desde, models.OrdenPago.fecha <= hasta))
    iva, n = db.execute(q).one()
    return {"desde": desde, "hasta": hasta, "iva_egresos": Decimal(iva),
            "cantidad_op": n}


def iva_gsoq_periodo(db: Session, desde, hasta) -> dict:
    """IVA de gastos de originación y quebranto por período (VFP: cb-iva-gsoq-periodo)."""
    q = (select(func.coalesce(func.sum(models.Solicitud.iva_gastos_originacion), 0),
                func.coalesce(func.sum(models.Solicitud.iva_quebranto), 0),
                func.count(models.Solicitud.id))
         .where(models.Solicitud.fecha_solicitud >= desde,
                models.Solicitud.fecha_solicitud <= hasta))
    iva_ori, iva_qeb, n = db.execute(q).one()
    return {"desde": desde, "hasta": hasta,
            "iva_gastos_originacion": Decimal(iva_ori),
            "iva_quebranto": Decimal(iva_qeb),
            "iva_total": Decimal(iva_ori) + Decimal(iva_qeb),
            "cantidad_solicitudes": n}


def op_devengadas(db: Session, desde, hasta) -> dict:
    """Órdenes de pago devengadas en el período, por tipo (VFP: cb-op-dev-periodo)."""
    from collections import defaultdict
    ops = db.scalars(select(models.OrdenPago).where(
        models.OrdenPago.fecha >= desde, models.OrdenPago.fecha <= hasta)
        .order_by(models.OrdenPago.fecha)).all()
    por_tipo = defaultdict(lambda: {"cantidad": 0, "total": Decimal("0")})
    total = Decimal("0")
    for o in ops:
        por_tipo[o.tipo]["cantidad"] += 1
        por_tipo[o.tipo]["total"] += o.importe
        total += o.importe
    return {"desde": desde, "hasta": hasta, "cantidad": len(ops), "total": total,
            "por_tipo": [{"tipo": t, "cantidad": v["cantidad"], "total": v["total"]}
                         for t, v in por_tipo.items()]}


def solicitudes_baja(db: Session) -> list[dict]:
    """Solicitudes dadas de baja/rechazadas, para revisión (VFP: cb-crevicredborra)."""
    q = (
        select(models.Solicitud, models.Cliente)
        .join(models.Cliente, models.Cliente.id == models.Solicitud.cliente_id)
        .where(models.Solicitud.estado == "B")
        .order_by(models.Solicitud.id.desc())
    )
    return [{"solicitud_id": s.id, "cliente": c.apellido_nombre, "cuil": c.cuil,
             "monto": s.monto_solicitado, "fecha": s.fecha_solicitud,
             "observaciones": s.observaciones}
            for s, c in db.execute(q).all()]


# ---------------- Reportes sobre el MAYOR REAL (movimientos_contables) ----------------
def balance_mayor(db: Session, *, desde: date | None = None,
                  hasta: date | None = None, periodo: str | None = None) -> dict:
    """Balance de sumas y saldos sobre el libro mayor real (VFP: asientos). Agrupa por
    cuenta: suma débitos y créditos y calcula el saldo (deudor/acreedor). Filtra por
    rango de fechas o por período (YYYYMM)."""
    M = models.MovimientoContable
    q = select(M.cuenta,
               func.coalesce(func.sum(M.debito), 0),
               func.coalesce(func.sum(M.credito), 0),
               func.count(M.id)).group_by(M.cuenta).order_by(M.cuenta)
    if periodo:
        q = q.where(M.periodo == periodo)
    if desde:
        q = q.where(M.fecha >= desde)
    if hasta:
        q = q.where(M.fecha <= hasta)
    filas = []
    tot_deb = tot_cred = CERO
    for cuenta, deb, cred, n in db.execute(q).all():
        deb, cred = Decimal(deb), Decimal(cred)
        saldo = deb - cred
        tot_deb += deb; tot_cred += cred
        filas.append({"cuenta": cuenta, "movimientos": n, "debito": deb,
                      "credito": cred,
                      "saldo_deudor": saldo if saldo > 0 else CERO,
                      "saldo_acreedor": -saldo if saldo < 0 else CERO})
    return {"cantidad_cuentas": len(filas), "total_debito": tot_deb,
            "total_credito": tot_cred, "cuadra": tot_deb == tot_cred, "cuentas": filas}


def mayor_cuenta(db: Session, *, cuenta: str, desde: date | None = None,
                 hasta: date | None = None, limit: int = 200, offset: int = 0) -> dict:
    """Movimientos (mayor) de una cuenta, con saldo acumulado. Paginado."""
    M = models.MovimientoContable
    base = select(M).where(M.cuenta == cuenta)
    if desde:
        base = base.where(M.fecha >= desde)
    if hasta:
        base = base.where(M.fecha <= hasta)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    tot_q = select(func.coalesce(func.sum(M.debito), 0),
                   func.coalesce(func.sum(M.credito), 0)).where(M.cuenta == cuenta)
    if desde:
        tot_q = tot_q.where(M.fecha >= desde)
    if hasta:
        tot_q = tot_q.where(M.fecha <= hasta)
    tot = db.execute(tot_q).one()
    rows = db.scalars(base.order_by(M.fecha, M.norden, M.id)
                      .limit(min(limit, 500)).offset(max(offset, 0))).all()
    items = [{"fecha": m.fecha, "periodo": m.periodo, "referencia": m.referencia,
              "debito": m.debito, "credito": m.credito} for m in rows]
    return {"cuenta": cuenta, "total": total, "limit": limit, "offset": offset,
            "total_debito": Decimal(tot[0]), "total_credito": Decimal(tot[1]),
            "saldo": Decimal(tot[0]) - Decimal(tot[1]), "items": items}


def iva_cuotas_cobradas(db: Session, *, desde: date | None = None,
                        hasta: date | None = None) -> dict:
    """IVA débito fiscal de cuotas de crédito cobradas por período (VFP:
    cb-cjcreditoscobrados / cb-iva-a-pagar-periodo, menú 61005/60505). Suma el IVA de
    las cuotas con `fecha_pago` en el rango (IVA de interés + seguro + gastos adm.),
    agrupado por período (YYYYMM). Fuente real: `maecuotas`."""
    C = models.Cuota
    iva_expr = (C.iva_interes + C.iva_seguro + C.iva_gastos_adm)
    per = func.to_char(C.fecha_pago, "YYYYMM") if db.bind.dialect.name == "postgresql" \
        else func.strftime("%Y%m", C.fecha_pago)
    q = (select(per.label("periodo"), func.count(C.id),
                func.coalesce(func.sum(C.iva_interes), 0),
                func.coalesce(func.sum(C.iva_seguro), 0),
                func.coalesce(func.sum(C.iva_gastos_adm), 0),
                func.coalesce(func.sum(iva_expr), 0))
         .where(C.fecha_pago.isnot(None)).group_by("periodo").order_by("periodo"))
    if desde:
        q = q.where(C.fecha_pago >= desde)
    if hasta:
        q = q.where(C.fecha_pago <= hasta)
    filas, tot = [], CERO
    for periodo, n, ivai, ivas, ivag, ivatot in db.execute(q).all():
        ivatot = Decimal(ivatot)
        tot += ivatot
        filas.append({"periodo": periodo, "cantidad": n,
                      "iva_interes": Decimal(ivai), "iva_seguro": Decimal(ivas),
                      "iva_gastos": Decimal(ivag), "iva_total": ivatot})
    return {"desde": desde, "hasta": hasta, "total_iva": tot,
            "cantidad_periodos": len(filas), "periodos": filas}


def ctacte_contable_credito(db: Session, no_credito: int) -> dict:
    """Cuenta corriente contable de un crédito (VFP: Contabilidad/crctacte.dbf).
    Movimientos con el desglose contable (capital, interés normal/punit/resarc,
    IVA, gastos, sellado) y totales."""
    C = models.CtaCteContableCredito
    filas = db.scalars(select(C).where(C.no_credito == no_credito)
                       .order_by(C.no_cuota, C.fecha_vto)).all()
    items = [{
        "cuenta": c.cuenta, "no_cuota": c.no_cuota, "fecha_vto": c.fecha_vto,
        "fecha_pago": c.fecha_pago, "via_pago": c.via_pago, "capital": c.capital,
        "int_normal": c.int_normal, "iva_normal": c.iva_normal, "gastos": c.gastos,
        "sellado": c.sellado, "int_punit": c.int_punit, "int_resarc": c.int_resarc,
        "debitos": c.debitos, "creditos": c.creditos, "saldo": c.saldo,
        "anulada": c.anulada,
    } for c in filas]
    tot = lambda f: sum((getattr(c, f) for c in filas), CERO)
    return {
        "no_credito": no_credito, "cantidad": len(items),
        "total_debitos": tot("debitos"), "total_creditos": tot("creditos"),
        "total_capital": tot("capital"), "total_int_normal": tot("int_normal"),
        "total_int_punit": tot("int_punit"), "saldo": tot("debitos") - tot("creditos"),
        "items": items,
    }


def contabilidad_general(db: Session, *, desde: date | None = None, hasta: date | None = None,
                         tipo: str | None = None, limit: int = 100, offset: int = 0) -> dict:
    """Contabilidad general de caja/juegos (VFP: Contabilidad/contgral.dbf): por
    asiento/recibo con importes por moneda; totales del filtro."""
    G = models.ContabilidadGeneral
    base = select(G)
    if desde:
        base = base.where(G.fecha >= desde)
    if hasta:
        base = base.where(G.fecha <= hasta)
    if tipo:
        base = base.where(G.tipo == tipo)
    sub = base.subquery()
    total = db.scalar(select(func.count()).select_from(sub)) or 0
    tp = Decimal(db.scalar(select(func.coalesce(func.sum(sub.c.total_pesos), 0))) or 0)
    tb = Decimal(db.scalar(select(func.coalesce(func.sum(sub.c.total_bonos), 0))) or 0)
    tl = Decimal(db.scalar(select(func.coalesce(func.sum(sub.c.total_lecop), 0))) or 0)
    filas = db.scalars(base.order_by(G.fecha.desc(), G.asiento.desc())
                       .limit(limit).offset(offset)).all()
    items = [{
        "fecha": g.fecha, "periodo": g.periodo, "asiento": g.asiento, "recibo": g.recibo,
        "tipo": g.tipo, "agencia": g.agencia, "destino": g.destino, "origen": g.origen,
        "sorteo": g.sorteo, "moneda": g.moneda, "total_pesos": g.total_pesos,
        "total_bonos": g.total_bonos, "total_lecop": g.total_lecop,
    } for g in filas]
    return {"total": total, "total_pesos": tp, "total_bonos": tb, "total_lecop": tl,
            "limit": limit, "offset": offset, "items": items}
