"""ABM de Categorias de gasto (sección 9 del diseño)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.catalog import ExpenseCategory
from app.models.audit import AuditEvent
from app.schemas.catalog_admin import CategoryOut, CategoryCreate, CategoryUpdate

router = APIRouter(prefix="/admin/categories", tags=["admin"])


def _get_or_404(db: Session, category_id: int) -> ExpenseCategory:
    cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return cat


def _to_out(db: Session, c: ExpenseCategory) -> dict:
    padre_nombre = None
    if c.categoria_padre_id:
        padre = db.query(ExpenseCategory).filter(ExpenseCategory.id == c.categoria_padre_id).first()
        padre_nombre = padre.nombre if padre else None
    return {
        "id": c.id,
        "nombre": c.nombre,
        "codigo_erp": c.codigo_erp,
        "categoria_padre_id": c.categoria_padre_id,
        "categoria_padre_nombre": padre_nombre,
        "is_active": c.is_active,
    }


@router.get("", response_model=list[CategoryOut])
def list_categories(
    incluir_inactivas: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ExpenseCategory)
    if not incluir_inactivas:
        q = q.filter(ExpenseCategory.is_active.is_(True))
    rows = q.order_by(ExpenseCategory.nombre).all()
    return [_to_out(db, r) for r in rows]


@router.post("", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    cat = ExpenseCategory(**payload.model_dump())
    db.add(cat)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="crear_categoria",
        entidad="expense_category", valor_nuevo_json=payload.model_dump(),
    ))
    db.commit()
    db.refresh(cat)
    return _to_out(db, cat)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    cat = _get_or_404(db, category_id)
    updates = payload.model_dump(exclude_unset=True)
    valor_anterior = {"nombre": cat.nombre, "codigo_erp": cat.codigo_erp, "categoria_padre_id": cat.categoria_padre_id}
    for campo, valor in updates.items():
        setattr(cat, campo, valor)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="editar_categoria",
        entidad="expense_category", entidad_id=cat.id,
        valor_anterior_json=valor_anterior, valor_nuevo_json=updates,
    ))
    db.commit()
    return _to_out(db, cat)


@router.delete("/{category_id}")
def deactivate_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    cat = _get_or_404(db, category_id)
    cat.is_active = False
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="desactivar_categoria",
        entidad="expense_category", entidad_id=cat.id,
    ))
    db.commit()
    return {"desactivada": True}
