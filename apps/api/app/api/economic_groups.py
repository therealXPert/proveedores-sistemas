"""
ABM de Grupos Economicos y asignacion de Empresas a cada grupo. Permite
filtrar el dashboard/reportes por "set de datos" del grupo activo (Autocity,
Grupo Tagle, Nuevos Negocios, etc.), agrupando las distintas razones
sociales/empresas que factura cada uno.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.catalog import EconomicGroup, Company
from app.models.invoicing import Invoice
from app.models.audit import AuditEvent
from app.schemas.economic_group import (
    EconomicGroupOut,
    EconomicGroupCreate,
    EconomicGroupUpdate,
    CompanyOut,
    CompanyUpdate,
)

router = APIRouter(tags=["economic_groups"])


def _get_group_or_404(db: Session, group_id: int) -> EconomicGroup:
    group = db.query(EconomicGroup).filter(EconomicGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo económico no encontrado")
    return group


@router.get("/economic-groups", response_model=list[EconomicGroupOut])
def list_economic_groups(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(EconomicGroup)
    if not incluir_inactivos:
        q = q.filter(EconomicGroup.is_active.is_(True))
    grupos = q.order_by(EconomicGroup.nombre).all()

    resultado = []
    for g in grupos:
        cantidad = db.query(func.count(Company.id)).filter(Company.economic_group_id == g.id).scalar()
        resultado.append({"id": g.id, "nombre": g.nombre, "is_active": g.is_active, "cantidad_empresas": cantidad or 0})
    return resultado


@router.post("/economic-groups", response_model=EconomicGroupOut)
def create_economic_group(
    payload: EconomicGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    grupo = EconomicGroup(nombre=payload.nombre)
    db.add(grupo)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="crear_grupo_economico",
        entidad="economic_group", valor_nuevo_json={"nombre": payload.nombre},
    ))
    db.commit()
    db.refresh(grupo)
    return {"id": grupo.id, "nombre": grupo.nombre, "is_active": grupo.is_active, "cantidad_empresas": 0}


@router.patch("/economic-groups/{group_id}", response_model=EconomicGroupOut)
def update_economic_group(
    group_id: int,
    payload: EconomicGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    grupo = _get_group_or_404(db, group_id)
    updates = payload.model_dump(exclude_unset=True)
    for campo, valor in updates.items():
        setattr(grupo, campo, valor)
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="editar_grupo_economico",
        entidad="economic_group", entidad_id=grupo.id, valor_nuevo_json=updates,
    ))
    db.commit()
    cantidad = db.query(func.count(Company.id)).filter(Company.economic_group_id == grupo.id).scalar()
    return {"id": grupo.id, "nombre": grupo.nombre, "is_active": grupo.is_active, "cantidad_empresas": cantidad or 0}


@router.delete("/economic-groups/{group_id}")
def deactivate_economic_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    grupo = _get_group_or_404(db, group_id)
    grupo.is_active = False
    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="desactivar_grupo_economico",
        entidad="economic_group", entidad_id=grupo.id,
    ))
    db.commit()
    return {"desactivado": True}


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    companies = db.query(Company).filter(Company.is_active.is_(True)).order_by(Company.nombre).all()
    resultado = []
    for c in companies:
        grupo = db.query(EconomicGroup).filter(EconomicGroup.id == c.economic_group_id).first() if c.economic_group_id else None
        cantidad_facturas = db.query(func.count(Invoice.id)).filter(Invoice.company_id == c.id).scalar()
        resultado.append({
            "id": c.id,
            "nombre": c.nombre,
            "economic_group_id": c.economic_group_id,
            "economic_group_nombre": grupo.nombre if grupo else None,
            "cantidad_facturas": cantidad_facturas or 0,
        })
    return resultado


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")

    valor_anterior = {"economic_group_id": company.economic_group_id}
    company.economic_group_id = payload.economic_group_id

    db.add(AuditEvent(
        user_id=current_user.id, fecha=datetime.utcnow(), accion="asignar_grupo_economico_empresa",
        entidad="company", entidad_id=company.id,
        valor_anterior_json=valor_anterior, valor_nuevo_json={"economic_group_id": payload.economic_group_id},
    ))
    db.commit()

    grupo = db.query(EconomicGroup).filter(EconomicGroup.id == company.economic_group_id).first() if company.economic_group_id else None
    cantidad_facturas = db.query(func.count(Invoice.id)).filter(Invoice.company_id == company.id).scalar()
    return {
        "id": company.id,
        "nombre": company.nombre,
        "economic_group_id": company.economic_group_id,
        "economic_group_nombre": grupo.nombre if grupo else None,
        "cantidad_facturas": cantidad_facturas or 0,
    }
