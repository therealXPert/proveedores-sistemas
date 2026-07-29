from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.catalog import Provider, ProviderAlias, ExpenseCategory
from app.models.invoicing import Invoice
from app.models.audit import AuditEvent
from app.schemas.provider import ProviderOut, ProviderUpdate, AliasCreate, ProviderAliasOut, MergeRequest
from app.services.provider_service import merge_providers

router = APIRouter(prefix="/providers", tags=["providers"])


def _get_provider_or_404(db: Session, provider_id: int) -> Provider:
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return provider


def _to_out(db: Session, provider: Provider) -> dict:
    cantidad_facturas = db.query(func.count(Invoice.id)).filter(Invoice.provider_id == provider.id).scalar()
    return {
        "id": provider.id,
        "nombre_normalizado": provider.nombre_normalizado,
        "razon_social": provider.razon_social,
        "cuit": provider.cuit,
        "categoria_principal_id": provider.categoria_principal_id,
        "categoria_principal_nombre": provider.categoria_principal.nombre if provider.categoria_principal else None,
        "moneda_habitual": provider.moneda_habitual,
        "condiciones_comerciales": provider.condiciones_comerciales,
        "observaciones": provider.observaciones,
        "aliases": provider.aliases,
        "cantidad_facturas": cantidad_facturas or 0,
    }


@router.get("", response_model=list[ProviderOut])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    providers = db.query(Provider).filter(Provider.is_active.is_(True)).order_by(Provider.nombre_normalizado).all()
    return [_to_out(db, p) for p in providers]


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = _get_provider_or_404(db, provider_id)
    return _to_out(db, provider)


@router.patch("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: int,
    payload: ProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    provider = _get_provider_or_404(db, provider_id)
    updates = payload.model_dump(exclude_unset=True)

    valor_anterior = {
        "nombre_normalizado": provider.nombre_normalizado,
        "razon_social": provider.razon_social,
        "cuit": provider.cuit,
        "categoria_principal_id": provider.categoria_principal_id,
        "moneda_habitual": provider.moneda_habitual,
        "condiciones_comerciales": provider.condiciones_comerciales,
        "observaciones": provider.observaciones,
    }

    for campo, valor in updates.items():
        setattr(provider, campo, valor)

    db.add(AuditEvent(
        user_id=current_user.id,
        fecha=datetime.utcnow(),
        accion="editar_proveedor",
        entidad="provider",
        entidad_id=provider.id,
        valor_anterior_json=valor_anterior,
        valor_nuevo_json=updates,
    ))
    db.commit()
    return _to_out(db, provider)


@router.post("/{provider_id}/aliases", response_model=ProviderAliasOut)
def add_alias(
    provider_id: int,
    payload: AliasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    provider = _get_provider_or_404(db, provider_id)
    texto = payload.alias_texto.strip()
    if not texto:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El alias no puede estar vacío")

    existente = db.query(ProviderAlias).filter(ProviderAlias.alias_texto == texto).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ese alias ya está en uso por el proveedor '{existente.provider.nombre_normalizado}'",
        )

    alias = ProviderAlias(provider_id=provider.id, alias_texto=texto)
    db.add(alias)
    db.add(AuditEvent(
        user_id=current_user.id,
        fecha=datetime.utcnow(),
        accion="agregar_alias_proveedor",
        entidad="provider",
        entidad_id=provider.id,
        valor_nuevo_json={"alias_texto": texto},
    ))
    db.commit()
    db.refresh(alias)
    return alias


@router.delete("/aliases/{alias_id}")
def delete_alias(
    alias_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    alias = db.query(ProviderAlias).filter(ProviderAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alias no encontrado")

    db.add(AuditEvent(
        user_id=current_user.id,
        fecha=datetime.utcnow(),
        accion="eliminar_alias_proveedor",
        entidad="provider",
        entidad_id=alias.provider_id,
        valor_anterior_json={"alias_texto": alias.alias_texto},
    ))
    db.delete(alias)
    db.commit()
    return {"eliminado": True}


@router.post("/{provider_id}/merge")
def merge(
    provider_id: int,
    payload: MergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    target = _get_provider_or_404(db, provider_id)
    other = _get_provider_or_404(db, payload.other_provider_id)
    try:
        resultado = merge_providers(db, target, other, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return resultado
