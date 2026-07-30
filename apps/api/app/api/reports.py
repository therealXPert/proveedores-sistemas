"""Dashboard ejecutivo y reportes (secciones 11 y 12 del diseño)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user
from app.models.security import User
from app.models.invoicing import Invoice
from app.models.catalog import Provider, Area, ExpenseCategory
from app.schemas.reports import (
    DashboardKPIs,
    EvolucionMensualItem,
    RankingProveedorItem,
    RankingCategoriaItem,
    RankingAreaItem,
    InvoiceListItem,
)
from app.services import reporting_service as rs

router = APIRouter(tags=["reports"])


@router.get("/dashboard", response_model=DashboardKPIs)
def dashboard(
    anio: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if anio is None or mes is None:
        anio_def, mes_def = rs.default_periodo(db)
        anio = anio or anio_def
        mes = mes or mes_def
    return rs.dashboard_kpis(db, anio, mes)


@router.get("/reports/evolucion-mensual", response_model=list[EvolucionMensualItem])
def evolucion_mensual(
    anio: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rs.evolucion_mensual(db, anio)


@router.get("/reports/por-proveedor", response_model=list[RankingProveedorItem])
def por_proveedor(
    anio: int = Query(...),
    mes: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rs.ranking_por_proveedor(db, anio, mes)


@router.get("/reports/por-categoria", response_model=list[RankingCategoriaItem])
def por_categoria(
    anio: int = Query(...),
    mes: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rs.ranking_por_categoria(db, anio, mes)


@router.get("/reports/por-area", response_model=list[RankingAreaItem])
def por_area(
    anio: int = Query(...),
    mes: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rs.ranking_por_area(db, anio, mes)


@router.get("/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    anio: int | None = None,
    mes: int | None = None,
    provider_id: int | None = None,
    area_id: int | None = None,
    category_id: int | None = None,
    moneda: str | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func

    q = db.query(Invoice).filter(Invoice.estado == "aprobado")
    if anio:
        q = q.filter(func.extract("year", Invoice.fecha_emision) == anio)
    if mes:
        q = q.filter(func.extract("month", Invoice.fecha_emision) == mes)
    if provider_id:
        q = q.filter(Invoice.provider_id == provider_id)
    if area_id:
        q = q.filter(Invoice.area_id == area_id)
    if category_id:
        q = q.filter(Invoice.category_id == category_id)
    if moneda:
        q = q.filter(Invoice.moneda == moneda)

    rows = q.order_by(Invoice.fecha_emision.desc()).limit(limit).all()

    resultado = []
    for inv in rows:
        provider = db.query(Provider).filter(Provider.id == inv.provider_id).first() if inv.provider_id else None
        area = db.query(Area).filter(Area.id == inv.area_id).first() if inv.area_id else None
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == inv.category_id).first() if inv.category_id else None
        aprobador = db.query(User).filter(User.id == inv.usuario_aprobador_id).first() if inv.usuario_aprobador_id else None

        resultado.append({
            "id": inv.id,
            "numero_factura": inv.numero_factura,
            "tipo_documento": inv.tipo_documento,
            "fecha_emision": inv.fecha_emision.isoformat() if inv.fecha_emision else "",
            "provider_nombre": provider.nombre_normalizado if provider else None,
            "area_nombre": area.nombre_normalizado if area else None,
            "category_nombre": category.nombre if category else None,
            "importe_total": float(inv.importe_total or 0),
            "moneda": inv.moneda,
            "descripcion": inv.descripcion,
            "usuario_aprobador_nombre": aprobador.nombre if aprobador else None,
            "import_batch_id": inv.import_batch_id,
            "link_documento_original": inv.link_documento_original,
        })
    return resultado


@router.get("/invoices/{invoice_id}", response_model=InvoiceListItem)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")

    provider = db.query(Provider).filter(Provider.id == inv.provider_id).first() if inv.provider_id else None
    area = db.query(Area).filter(Area.id == inv.area_id).first() if inv.area_id else None
    category = db.query(ExpenseCategory).filter(ExpenseCategory.id == inv.category_id).first() if inv.category_id else None
    aprobador = db.query(User).filter(User.id == inv.usuario_aprobador_id).first() if inv.usuario_aprobador_id else None

    return {
        "id": inv.id,
        "numero_factura": inv.numero_factura,
        "tipo_documento": inv.tipo_documento,
        "fecha_emision": inv.fecha_emision.isoformat() if inv.fecha_emision else "",
        "provider_nombre": provider.nombre_normalizado if provider else None,
        "area_nombre": area.nombre_normalizado if area else None,
        "category_nombre": category.nombre if category else None,
        "importe_total": float(inv.importe_total or 0),
        "moneda": inv.moneda,
        "descripcion": inv.descripcion,
        "usuario_aprobador_nombre": aprobador.nombre if aprobador else None,
        "import_batch_id": inv.import_batch_id,
        "link_documento_original": inv.link_documento_original,
    }
