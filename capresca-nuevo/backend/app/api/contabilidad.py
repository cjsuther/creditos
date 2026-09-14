"""Módulo Contabilidad: libro diario (asientos generados automáticamente)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.deps import get_current_user
from app.reports.pdf import libro_diario_pdf, iva_periodo_pdf, balance_sumas_saldos_pdf
from app.services import contabilidad as svc
from app import models, schemas

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"],
                   dependencies=[Depends(get_current_user)])


@router.get("/libro-diario", response_model=list[schemas.AsientoOut])
def libro_diario(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
):
    qy = select(models.Asiento).options(selectinload(models.Asiento.lineas))
    if desde:
        qy = qy.where(models.Asiento.fecha >= desde)
    if hasta:
        qy = qy.where(models.Asiento.fecha <= hasta)
    return db.scalars(qy.order_by(models.Asiento.fecha, models.Asiento.id)).all()


@router.get("/balance")
def balance_sumas_saldos(desde: date | None = None, hasta: date | None = None,
                         db: Session = Depends(get_db)):
    """Balance de sumas y saldos del período (VFP: balance de comprobación)."""
    return svc.balance_sumas_saldos(db, desde, hasta)


@router.get("/iva-cuotas")
def iva_cuotas_cobradas(desde: date | None = None, hasta: date | None = None,
                        db: Session = Depends(get_db)):
    """IVA débito de cuotas de crédito cobradas por período, sobre dato real
    (`maecuotas`). VFP: cb-cjcreditoscobrados (61005/60505)."""
    return svc.iva_cuotas_cobradas(db, desde=desde, hasta=hasta)


@router.get("/ctacte-credito")
def ctacte_contable_credito(no_credito: int, db: Session = Depends(get_db)):
    """Cta. cte. contable de un crédito (crctacte.dbf): desglose contable + totales."""
    return svc.ctacte_contable_credito(db, no_credito)


@router.get("/general")
def contabilidad_general(desde: date | None = None, hasta: date | None = None,
                         tipo: str | None = None, limit: int = Query(100, le=500),
                         offset: int = 0, db: Session = Depends(get_db)):
    """Contabilidad general de caja/juegos (contgral.dbf): asientos + totales por moneda."""
    return svc.contabilidad_general(db, desde=desde, hasta=hasta, tipo=tipo,
                                    limit=limit, offset=offset)


@router.get("/mayor/balance")
def balance_mayor(desde: date | None = None, hasta: date | None = None,
                  periodo: str | None = None, db: Session = Depends(get_db)):
    """Balance de sumas y saldos sobre el LIBRO MAYOR REAL (asientos migrados, 2M)."""
    return svc.balance_mayor(db, desde=desde, hasta=hasta, periodo=periodo)


@router.get("/mayor/cuenta")
def mayor_cuenta(cuenta: str = Query(...), desde: date | None = None,
                 hasta: date | None = None,
                 limit: int = Query(default=200, le=500), offset: int = 0,
                 db: Session = Depends(get_db)):
    """Movimientos (mayor) de una cuenta contable sobre el dato real."""
    return svc.mayor_cuenta(db, cuenta=cuenta, desde=desde, hasta=hasta,
                            limit=limit, offset=offset)


@router.get("/balance/pdf")
def balance_pdf_endpoint(desde: date | None = None, hasta: date | None = None,
                         db: Session = Depends(get_db)):
    pdf = balance_sumas_saldos_pdf(svc.balance_sumas_saldos(db, desde, hasta))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="balance_sumas_saldos.pdf"'})


@router.get("/libro-diario/pdf")
def libro_diario_pdf_endpoint(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
):
    qy = select(models.Asiento).options(selectinload(models.Asiento.lineas))
    if desde:
        qy = qy.where(models.Asiento.fecha >= desde)
    if hasta:
        qy = qy.where(models.Asiento.fecha <= hasta)
    asientos = db.scalars(qy.order_by(models.Asiento.fecha, models.Asiento.id)).all()
    pdf = libro_diario_pdf(asientos)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="libro_diario.pdf"'})


@router.get("/iva-periodo", response_model=schemas.IvaPeriodo)
def iva_periodo(desde: date, hasta: date, db: Session = Depends(get_db)):
    return svc.iva_periodo(db, desde, hasta)


@router.get("/iva-periodo/pdf")
def iva_periodo_pdf_endpoint(desde: date, hasta: date, db: Session = Depends(get_db)):
    data = svc.iva_periodo(db, desde, hasta)
    pdf = iva_periodo_pdf(data)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="iva_{desde}_{hasta}.pdf"'})


@router.get("/op-devengadas", response_model=schemas.OpDevengadas)
def op_devengadas(desde: date, hasta: date, db: Session = Depends(get_db)):
    """Órdenes de pago devengadas por período, agrupadas por tipo."""
    return svc.op_devengadas(db, desde, hasta)


@router.get("/iva-egresos")
def iva_egresos(desde: date, hasta: date, db: Session = Depends(get_db)):
    """IVA de egresos de créditos por período (cb-egivaegresos)."""
    return svc.iva_egresos(db, desde, hasta)


@router.get("/iva-gsoq")
def iva_gsoq(desde: date, hasta: date, db: Session = Depends(get_db)):
    """IVA de gastos de originación y quebranto por período (cb-iva-gsoq-periodo)."""
    return svc.iva_gsoq_periodo(db, desde, hasta)


@router.get("/solicitudes-baja", response_model=list[schemas.SolicitudBaja])
def solicitudes_baja(db: Session = Depends(get_db)):
    """Solicitudes dadas de baja / rechazadas, para revisión."""
    return svc.solicitudes_baja(db)


@router.get("/asientos/{asiento_id}", response_model=schemas.AsientoOut)
def obtener_asiento(asiento_id: int, db: Session = Depends(get_db)):
    a = db.get(models.Asiento, asiento_id)
    if not a:
        raise HTTPException(404, "Asiento no encontrado")
    return a
