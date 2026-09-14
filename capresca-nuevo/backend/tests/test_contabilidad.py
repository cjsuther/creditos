"""Contabilidad automática y cierre de caja."""
import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./_cont.db"
os.environ["ENVIRONMENT"] = "development"

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def _auth(client):
    r = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _otorgar(client, h, cuotas=3, primer_vto="2026-01-10"):
    cli = client.get("/api/clientes", headers=h).json()["items"][0]["id"]
    lineas = client.get("/api/creditos/lineas", headers=h).json()
    linea = next(l for l in lineas if l["tipo_calculo"] == 1)
    s = client.post("/api/creditos/solicitudes", headers=h, json={
        "cliente_id": cli, "linea_id": linea["id"],
        "monto_solicitado": "90000", "cantidad_cuotas": cuotas,
        "fecha_primer_vencimiento": primer_vto,
    }).json()
    return client.post(f"/api/creditos/solicitudes/{s['id']}/otorgar", headers=h).json()


def _balance(asiento):
    debe = sum(Decimal(l["debe"]) for l in asiento["lineas"])
    haber = sum(Decimal(l["haber"]) for l in asiento["lineas"])
    return debe, haber


def test_asiento_otorgamiento_balanceado(client):
    h = _auth(client)
    cred = _otorgar(client, h)
    diario = client.get("/api/contabilidad/libro-diario", headers=h).json()
    otorg = [a for a in diario if a["origen"] == "otorgamiento" and a["ref_id"] == cred["id"]]
    assert len(otorg) == 1
    debe, haber = _balance(otorg[0])
    assert debe == haber == Decimal("90000.00")
    # créditos a cobrar al debe, caja al haber
    codigos = {l["cuenta_codigo"] for l in otorg[0]["lineas"]}
    assert "1.2.01" in codigos and "1.1.01" in codigos


def test_asiento_cobranza_balanceado(client):
    h = _auth(client)
    cred = _otorgar(client, h)
    r = client.post("/api/caja/cobrar", headers=h, json={
        "credito_id": cred["id"], "cuotas": [1], "fecha_pago": "2026-01-10",
    }).json()
    diario = client.get("/api/contabilidad/libro-diario", headers=h).json()
    cob = [a for a in diario if a["origen"] == "cobranza" and a["ref_id"] == r["id"]]
    assert len(cob) == 1
    debe, haber = _balance(cob[0])
    assert debe == haber
    assert debe == Decimal(str(r["total"]))  # debe (caja) = total del recibo


def test_cierre_de_caja(client):
    h = _auth(client)
    cred = _otorgar(client, h)
    # fecha de cobro única para aislar el cierre de otros tests que comparten DB
    fecha = "2026-06-01"
    client.post("/api/caja/cobrar", headers=h, json={
        "credito_id": cred["id"], "cuotas": [1, 2], "fecha_pago": fecha,
    })
    cierre = client.get(f"/api/caja/cierre?fecha={fecha}", headers=h).json()
    assert cierre["cantidad_recibos"] == 1
    assert Decimal(cierre["total_cobrado"]) > 0
    conceptos = {c["concepto"] for c in cierre["por_concepto"]}
    assert "Capital" in conceptos and "Interés" in conceptos


def teardown_module(_):
    if os.path.exists("_cont.db"):
        os.remove("_cont.db")


def test_balance_sumas_saldos_cuadra(client):
    h = _auth(client)
    _otorgar(client, h)  # genera asiento de otorgamiento
    b = client.get("/api/contabilidad/balance", headers=h).json()
    assert b["cuentas"], "debe haber cuentas con movimiento"
    # sumas iguales y saldos iguales -> cuadra
    assert Decimal(b["total"]["debe"]) == Decimal(b["total"]["haber"])
    assert Decimal(b["total"]["deudor"]) == Decimal(b["total"]["acreedor"])
    assert b["cuadra"] is True
    # PDF
    pdf = client.get("/api/contabilidad/balance/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_balance_y_mayor_real(client):
    """Balance y mayor sobre el libro mayor real (movimientos_contables)."""
    h = _auth(client)
    import datetime
    from decimal import Decimal
    from app.core.database import SessionLocal
    from app import models
    db = SessionLocal()
    db.add(models.MovimientoContable(cuenta="PPS/DE", periodo="202405",
        fecha=datetime.date(2024, 5, 17), norden=1, debito=Decimal("1000"), credito=Decimal("0")))
    db.add(models.MovimientoContable(cuenta="PPS/DE", periodo="202405",
        fecha=datetime.date(2024, 5, 18), norden=2, debito=Decimal("0"), credito=Decimal("300")))
    db.add(models.MovimientoContable(cuenta="PPC/DE", periodo="202405",
        fecha=datetime.date(2024, 5, 18), norden=3, debito=Decimal("500"), credito=Decimal("0")))
    db.commit(); db.close()

    bal = client.get("/api/contabilidad/mayor/balance?periodo=202405", headers=h).json()
    ppsde = next(c for c in bal["cuentas"] if c["cuenta"] == "PPS/DE")
    assert Decimal(ppsde["debito"]) == Decimal("1000.00")
    assert Decimal(ppsde["credito"]) == Decimal("300.00")
    assert Decimal(ppsde["saldo_deudor"]) == Decimal("700.00")   # 1000 - 300
    assert Decimal(bal["total_debito"]) == Decimal("1500.00")

    may = client.get("/api/contabilidad/mayor/cuenta?cuenta=PPS/DE", headers=h).json()
    assert may["total"] == 2 and Decimal(may["saldo"]) == Decimal("700.00")


def test_iva_cuotas_cobradas_real(client):
    """IVA de cuotas cobradas por período sobre dato real (maecuotas)."""
    h = _auth(client)
    import datetime
    from decimal import Decimal
    from app.core.database import SessionLocal
    from app import models
    cli_id = client.get("/api/clientes", headers=h).json()["items"][0]["id"]
    db = SessionLocal()
    # crédito + cuota pagada con IVA
    cr = models.Credito(cliente_id=cli_id, capital=Decimal("1000"),
                        saldo_capital=Decimal("0"), estado="A")
    db.add(cr); db.flush()
    db.add(models.Cuota(credito_id=cr.id, numero=1, fecha_vencimiento=datetime.date(2025, 3, 10),
        saldo_capital=Decimal("0"), amortizacion=Decimal("100"), interes=Decimal("50"),
        iva_interes=Decimal("10.50"), seguro=Decimal("0"), iva_seguro=Decimal("0"),
        gastos_adm=Decimal("0"), iva_gastos_adm=Decimal("2.00"), total=Decimal("162.50"),
        total_pagado=Decimal("162.50"), estado="P", fecha_pago=datetime.date(2025, 3, 15)))
    db.commit(); db.close()

    d = client.get("/api/contabilidad/iva-cuotas?desde=2025-03-01&hasta=2025-03-31", headers=h).json()
    assert Decimal(d["total_iva"]) == Decimal("12.50")   # 10.50 + 2.00
    p = next(x for x in d["periodos"] if x["periodo"] == "202503")
    assert Decimal(p["iva_interes"]) == Decimal("10.50") and Decimal(p["iva_gastos"]) == Decimal("2.00")
