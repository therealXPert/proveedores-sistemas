from typing import Optional

from pydantic import BaseModel


class ProviderAliasOut(BaseModel):
    id: int
    alias_texto: str

    model_config = {"from_attributes": True}


class ProviderOut(BaseModel):
    id: int
    nombre_normalizado: str
    razon_social: Optional[str] = None
    cuit: Optional[str] = None
    categoria_principal_id: Optional[int] = None
    categoria_principal_nombre: Optional[str] = None
    moneda_habitual: Optional[str] = None
    condiciones_comerciales: Optional[str] = None
    observaciones: Optional[str] = None
    aliases: list[ProviderAliasOut] = []
    cantidad_facturas: int = 0


class ProviderUpdate(BaseModel):
    nombre_normalizado: Optional[str] = None
    razon_social: Optional[str] = None
    cuit: Optional[str] = None
    categoria_principal_id: Optional[int] = None
    moneda_habitual: Optional[str] = None
    condiciones_comerciales: Optional[str] = None
    observaciones: Optional[str] = None


class AliasCreate(BaseModel):
    alias_texto: str


class MergeRequest(BaseModel):
    other_provider_id: int
