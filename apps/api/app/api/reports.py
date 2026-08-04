"""Dashboard ejecutivo y reportes (secciones 11 y 12 del diseño). Trabaja sobre un rango de fechas libre."""
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
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
from app.services import export_service as ex

router = APIRouter(tags=["reports"])


def _resolver_rango(db: Session, fecha_desde: date | None, fecha_hasta: date | None) -> tuple[date, date]:
    if fecha_desde and fecha_hasta:
        if fecha_desde > fecha_hasta:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fecha_desde no puede ser posterior a fecha_hasta")
        return fecha_desde, fecha_hasta
    return rs.default_rango(db)


@router.get("/dashboard", response_model=DashboardKPIs)
def dashboard(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    desde, hasta = _resolver_rango(db, fecha_desde, fecha_hasta)
    return rs.dashboard_kpis(db, desde, hasta, economic_group_id)


@router.get("/reports/evolucion-mensual", response_model=list[EvolucionMensualItem])
def evolucion_mensual(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    desde, hasta = _resolver_rango(db, fecha_desde, fecha_hasta)
    return rs.evolucion_mensual(db, desde, hasta, economic_group_id)


@router.get("/reports/por-proveedor", response_model=list[RankingProveedorItem])
def por_proveedor(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    desde, hasta = _resolver_rango(db, fecha_desde, fecha_hasta)
    return rs.ranking_por_proveedor(db, desde, hasta, economic_group_id)


@router.get("/reports/por-categoria", response_model=list[RankingCategoriaItem])
def por_categoria(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    desde, hasta = _resolver_rango(db, fecha_desde, fecha_hasta)
    return rs.ranking_por_categoria(db, desde, hasta, economic_group_id)


@router.get("/reports/por-area", response_model=list[RankingAreaItem])
def por_area(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    desde, hasta = _resolver_rango(db, fecha_desde, fecha_hasta)
    return rs.ranking_por_area(db, desde, hasta, economic_group_id)


def _invoice_filtered_query(db: Session, fecha_desde, fecha_hasta, provider_id, area_id, category_id, moneda, economic_group_id=None):
    q = db.query(Invoice).filter(Invoice.estado == "aprobado")
    if fecha_desde:
        q = q.filter(Invoice.fecha_emision >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Invoice.fecha_emision <= datetime.combine(fecha_hasta, datetime.max.time()))
    if provider_id:
        q = q.filter(Invoice.provider_id == provider_id)
    if area_id:
        q = q.filter(Invoice.area_id == area_id)
    if category_id:
        q = q.filter(Invoice.category_id == category_id)
    if moneda:
        q = q.filter(Invoice.moneda == moneda)
    if economic_group_id:
        q = q.filter(Invoice.economic_group_id == economic_group_id)
    return q.order_by(Invoice.fecha_emision.desc())


def _invoice_to_dict(db: Session, inv: Invoice) -> dict:
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


@router.get("/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    provider_id: int | None = None,
    area_id: int | None = None,
    category_id: int | None = None,
    moneda: str | None = None,
    economic_group_id: int | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _invoice_filtered_query(db, fecha_desde, fecha_hasta, provider_id, area_id, category_id, moneda, economic_group_id).limit(limit).all()
    return [_invoice_to_dict(db, inv) for inv in rows]


@router.get("/invoices/export")
def export_invoices(
    formato: str = Query(..., pattern="^(csv|xlsx)$"),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    provider_id: int | None = None,
    area_id: int | None = None,
    category_id: int | None = None,
    moneda: str | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta el detalle de facturas respetando los mismos filtros de la pantalla (sección 15 del diseño)."""
    rows = _invoice_filtered_query(db, fecha_desde, fecha_hasta, provider_id, area_id, category_id, moneda, economic_group_id).limit(5000).all()
    data = [_invoice_to_dict(db, inv) for inv in rows]

    if formato == "csv":
        contenido = ex.invoices_to_csv(data)
        media_type = "text/csv"
        nombre = "facturas.csv"
    else:
        contenido = ex.invoices_to_xlsx(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        nombre = "facturas.xlsx"

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/dashboard/export-pdf")
def export_dashboard_pdf(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    economic_group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe ejecutivo en PDF (sección 15 del diseño)."""
    desde, hasta = _resolver_rango(db, fecha_desde, fecha_hasta)

    kpis = rs.dashboard_kpis(db, desde, hasta, economic_group_id)
    top_proveedores = rs.ranking_por_proveedor(db, desde, hasta, economic_group_id)
    contenido = ex.dashboard_to_pdf(kpis, top_proveedores)

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-ejecutivo-{desde.isoformat()}_a_{hasta.isoformat()}.pdf"'},
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceListItem)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return _invoice_to_dict(db, inv)
