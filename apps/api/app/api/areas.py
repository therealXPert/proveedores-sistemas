"""ABM de Areas (sección 9 del diseño), con el mismo patron de alias que Proveedores."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.catalog import Area, AreaAlias
from app.models.invoicing import Invoice
from app.models.audit import AuditEvent
from app.schemas.catalog_admin import AreaOut, AreaCreate, AreaUpdate
from app.schemas.provider import AliasCreate

router = APIRouter(prefix="/admin/areas", tags=["admin"])


def _get_or_404(db: Session, area_id: int) -> Area:
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada")
    return area


def _to_out(db: Session, area: Area) -> dict:
    cantidad_facturas = db.query(func.count(Invoice.id)).filter(Invoice.area_id == area.id).scalar()
    return {
        "id": area.id,
        "nombre_normalizado": area.nombre_normalizado,
        "is_active": area.is_active,
        "aliases": area.aliases,
        "cantidad_facturas": cantidad_facturas or 0,
    }


@router.get("", response_model=list[AreaOut])
def list_areas(
    incluir_inactivas: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Area)
    if not incluir_inactivas:
        q = q.filter(Area.is_active.is_(True))
    rows = q.order_by(Area.nombre_normalizado).all()
    return [_to_out(db, r) for r in rows]


@router.post("", response_model=AreaOut)
def create_area(
    payload: AreaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    area = Area(nombre_normalizado=payload.nombre_normalizado)
    db.add(area)
    db.flush()
    db.add(AreaAlias(area_id=area.id, alias_texto=payload.nombre_normalizado))
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="crear_area",
        entidad="area", entidad_id=area.id, valor_nuevo_json={"nombre": payload.nombre_normalizado},
    ))
    db.commit()
    return _to_out(db, area)


@router.patch("/{area_id}", response_model=AreaOut)
def update_area(
    area_id: int,
    payload: AreaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    area = _get_or_404(db, area_id)
    updates = payload.model_dump(exclude_unset=True)
    valor_anterior = {"nombre_normalizado": area.nombre_normalizado}
    for campo, valor in updates.items():
        setattr(area, campo, valor)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="editar_area",
        entidad="area", entidad_id=area.id, valor_anterior_json=valor_anterior, valor_nuevo_json=updates,
    ))
    db.commit()
    return _to_out(db, area)


@router.delete("/{area_id}")
def deactivate_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    area = _get_or_404(db, area_id)
    area.is_active = False
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="desactivar_area", entidad="area", entidad_id=area.id,
    ))
    db.commit()
    return {"desactivada": True}


@router.post("/{area_id}/aliases")
def add_alias(
    area_id: int,
    payload: AliasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    area = _get_or_404(db, area_id)
    texto = payload.alias_texto.strip()
    if not texto:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El alias no puede estar vacío")

    existente = db.query(AreaAlias).filter(AreaAlias.alias_texto == texto).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ese alias ya está en uso por el área '{existente.area.nombre_normalizado}'",
        )

    alias = AreaAlias(area_id=area.id, alias_texto=texto)
    db.add(alias)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="agregar_alias_area",
        entidad="area", entidad_id=area.id, valor_nuevo_json={"alias_texto": texto},
    ))
    db.commit()
    db.refresh(alias)
    return {"id": alias.id, "alias_texto": alias.alias_texto}


@router.delete("/aliases/{alias_id}")
def delete_alias(
    alias_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    alias = db.query(AreaAlias).filter(AreaAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alias no encontrado")
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="eliminar_alias_area",
        entidad="area", entidad_id=alias.area_id, valor_anterior_json={"alias_texto": alias.alias_texto},
    ))
    db.delete(alias)
    db.commit()
    return {"eliminado": True}
