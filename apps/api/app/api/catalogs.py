"""
Listados simples de catalogos (solo lectura), usados para llenar los selects
del formulario de edicion de facturas en staging. La administracion completa
(ABM, fusion de proveedores, etc.) es una etapa aparte -- esto es lo minimo
para poder elegir un valor existente al editar.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user
from app.models.catalog import (
    Provider,
    Area,
    ExpenseCategory,
    CostCenter,
    BusinessUnit,
    Company,
    Branch,
)
from app.schemas.catalog import CatalogItem

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@router.get("/providers", response_model=list[CatalogItem])
def list_providers(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(Provider).filter(Provider.is_active.is_(True)).order_by(Provider.nombre_normalizado).all()
    return [{"id": r.id, "nombre": r.nombre_normalizado} for r in rows]


@router.get("/areas", response_model=list[CatalogItem])
def list_areas(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(Area).filter(Area.is_active.is_(True)).order_by(Area.nombre_normalizado).all()
    return [{"id": r.id, "nombre": r.nombre_normalizado} for r in rows]


@router.get("/categories", response_model=list[CatalogItem])
def list_categories(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(ExpenseCategory).filter(ExpenseCategory.is_active.is_(True)).order_by(ExpenseCategory.nombre).all()
    return [{"id": r.id, "nombre": f"{r.nombre} ({r.codigo_erp})" if r.codigo_erp else r.nombre} for r in rows]


@router.get("/cost-centers", response_model=list[CatalogItem])
def list_cost_centers(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(CostCenter).filter(CostCenter.is_active.is_(True)).order_by(CostCenter.codigo).all()
    return [{"id": r.id, "nombre": f"{r.codigo} - {r.nombre}"} for r in rows]


@router.get("/business-units", response_model=list[CatalogItem])
def list_business_units(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(BusinessUnit).filter(BusinessUnit.is_active.is_(True)).order_by(BusinessUnit.nombre).all()
    return [{"id": r.id, "nombre": r.nombre} for r in rows]


@router.get("/companies", response_model=list[CatalogItem])
def list_companies(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(Company).filter(Company.is_active.is_(True)).order_by(Company.nombre).all()
    return [{"id": r.id, "nombre": r.nombre} for r in rows]


@router.get("/branches", response_model=list[CatalogItem])
def list_branches(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(Branch).filter(Branch.is_active.is_(True)).order_by(Branch.nombre).all()
    return [{"id": r.id, "nombre": r.nombre} for r in rows]
