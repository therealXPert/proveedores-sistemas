"""
Modulo de presupuesto (sección 10 del diseño). CRUD basico sobre 'budgets'
mas un resumen que compara el presupuesto mensual contra el gasto real
(a partir de las facturas ya aprobadas) por proveedor.

Limitacion conocida: el diseño original pide versionar presupuestos
(original/revisado/vigente) sin sobrescribir. Por ahora el CRUD edita/borra
directamente sobre la version 'vigente' -- no hay todavia una pantalla para
comparar versiones entre si. Documentado en docs/decisiones-arquitectura.md.
"""
from datetime import datetime
from decimal import Decimal
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.budget import Budget, BudgetVersion
from app.models.catalog import Provider, Area, ExpenseCategory, CostCenter, BusinessUnit
from app.models.invoicing import Invoice
from app.models.audit import AuditEvent
from app.schemas.budget import BudgetOut, BudgetCreate, BudgetUpdate, BudgetResumenItem
from app.services.budget_import_service import _periodicidad_a_mensual
from app.services import export_service as ex

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _get_or_create_vigente_version(db: Session, anio: int) -> BudgetVersion:
    nombre = f"Presupuesto {anio} - vigente"
    version = db.query(BudgetVersion).filter(BudgetVersion.nombre == nombre).first()
    if not version:
        version = BudgetVersion(nombre=nombre, tipo="vigente")
        db.add(version)
        db.flush()
    return version


def _to_out(db: Session, b: Budget) -> dict:
    def _nombre(modelo, id_, campo="nombre"):
        if not id_:
            return None
        obj = db.query(modelo).filter(modelo.id == id_).first()
        return getattr(obj, campo) if obj else None

    return {
        "id": b.id,
        "anio": b.anio,
        "mes": b.mes,
        "provider_id": b.provider_id,
        "provider_nombre": _nombre(Provider, b.provider_id, "nombre_normalizado"),
        "area_id": b.area_id,
        "area_nombre": _nombre(Area, b.area_id, "nombre_normalizado"),
        "category_id": b.category_id,
        "category_nombre": _nombre(ExpenseCategory, b.category_id, "nombre"),
        "cost_center_id": b.cost_center_id,
        "cost_center_nombre": _nombre(CostCenter, b.cost_center_id, "nombre"),
        "business_unit_id": b.business_unit_id,
        "business_unit_nombre": _nombre(BusinessUnit, b.business_unit_id, "nombre"),
        "moneda": b.moneda,
        "periodicidad_original": b.periodicidad_original,
        "importe_original": float(b.importe_original) if b.importe_original is not None else None,
        "importe_mensual_equivalente": float(b.importe_mensual_equivalente) if b.importe_mensual_equivalente is not None else None,
        "comentario": b.comentario,
    }


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    anio: int = 2026,
    provider_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Budget).filter(Budget.anio == anio)
    if provider_id:
        q = q.filter(Budget.provider_id == provider_id)
    rows = q.order_by(Budget.id).all()
    return [_to_out(db, r) for r in rows]


@router.post("", response_model=BudgetOut)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    version = _get_or_create_vigente_version(db, payload.anio)

    importe = Decimal(str(payload.importe_original)) if payload.importe_original is not None else None
    mensual = _periodicidad_a_mensual(importe, payload.periodicidad_original)

    budget = Budget(
        budget_version_id=version.id,
        anio=payload.anio,
        mes=payload.mes,
        provider_id=payload.provider_id,
        area_id=payload.area_id,
        category_id=payload.category_id,
        cost_center_id=payload.cost_center_id,
        business_unit_id=payload.business_unit_id,
        moneda=payload.moneda,
        periodicidad_original=payload.periodicidad_original,
        importe_original=importe,
        importe_mensual_equivalente=mensual,
        comentario=payload.comentario,
    )
    db.add(budget)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="crear_presupuesto",
        entidad="budget", valor_nuevo_json=payload.model_dump(),
    ))
    db.commit()
    db.refresh(budget)
    return _to_out(db, budget)


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presupuesto no encontrado")

    updates = payload.model_dump(exclude_unset=True)
    for campo, valor in updates.items():
        if campo == "importe_original" and valor is not None:
            setattr(budget, campo, Decimal(str(valor)))
        else:
            setattr(budget, campo, valor)

    # Si cambio el importe o la periodicidad, se recalcula el equivalente mensual
    if "importe_original" in updates or "periodicidad_original" in updates:
        budget.importe_mensual_equivalente = _periodicidad_a_mensual(
            budget.importe_original, budget.periodicidad_original
        )

    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="editar_presupuesto",
        entidad="budget", entidad_id=budget.id, valor_nuevo_json=updates,
    ))
    db.commit()
    return _to_out(db, budget)


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presupuesto no encontrado")
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="eliminar_presupuesto",
        entidad="budget", entidad_id=budget.id,
        valor_anterior_json={"provider_id": budget.provider_id, "importe_original": float(budget.importe_original or 0)},
    ))
    db.delete(budget)
    db.commit()
    return {"eliminado": True}


def _resumen_data(db: Session, anio: int) -> list[dict]:
    presupuestos = db.query(Budget).filter(Budget.anio == anio, Budget.provider_id.isnot(None)).all()

    por_proveedor: dict[int, Decimal] = {}
    for b in presupuestos:
        if b.importe_mensual_equivalente:
            por_proveedor[b.provider_id] = por_proveedor.get(b.provider_id, Decimal(0)) + b.importe_mensual_equivalente

    resultado = []
    for provider_id, presupuesto_mensual in por_proveedor.items():
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            continue

        invoices = db.query(Invoice).filter(
            Invoice.provider_id == provider_id,
            Invoice.estado == "aprobado",
            Invoice.moneda.in_(["Pesos", "ARS"]),
        ).all()

        gasto_real_total = sum((inv.importe_total or Decimal(0) for inv in invoices), Decimal(0))
        meses_con_gasto = {(inv.fecha_emision.year, inv.fecha_emision.month) for inv in invoices if inv.fecha_emision}
        cantidad_meses = len(meses_con_gasto) or 1
        gasto_real_promedio_mensual = gasto_real_total / cantidad_meses

        resultado.append({
            "provider_id": provider_id,
            "provider_nombre": provider.nombre_normalizado,
            "presupuesto_mensual": float(presupuesto_mensual),
            "gasto_real_promedio_mensual": float(gasto_real_promedio_mensual),
            "gasto_real_total": float(gasto_real_total),
            "desvio_mensual": float(gasto_real_promedio_mensual - presupuesto_mensual),
        })

    resultado.sort(key=lambda r: -abs(r["desvio_mensual"]))
    return resultado


@router.get("/resumen", response_model=list[BudgetResumenItem])
def resumen(
    anio: int = 2026,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compara el presupuesto mensual contra el gasto real acumulado, por proveedor."""
    return _resumen_data(db, anio)


@router.get("/resumen/export")
def export_resumen(
    formato: str = Query(..., pattern="^(csv|xlsx)$"),
    anio: int = 2026,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta el resumen presupuesto vs. gasto real (sección 15 del diseño)."""
    data = _resumen_data(db, anio)

    if formato == "csv":
        contenido = ex.budget_resumen_to_csv(data)
        media_type = "text/csv"
        nombre = f"presupuesto-vs-real-{anio}.csv"
    else:
        contenido = ex.budget_resumen_to_xlsx(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        nombre = f"presupuesto-vs-real-{anio}.xlsx"

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
