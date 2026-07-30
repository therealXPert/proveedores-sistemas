from typing import Optional

from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    nombre: str
    codigo_erp: Optional[str] = None
    categoria_padre_id: Optional[int] = None
    categoria_padre_nombre: Optional[str] = None
    is_active: bool


class CategoryCreate(BaseModel):
    nombre: str
    codigo_erp: Optional[str] = None
    categoria_padre_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    nombre: Optional[str] = None
    codigo_erp: Optional[str] = None
    categoria_padre_id: Optional[int] = None


class AreaAliasOut(BaseModel):
    id: int
    alias_texto: str

    model_config = {"from_attributes": True}


class AreaOut(BaseModel):
    id: int
    nombre_normalizado: str
    is_active: bool
    aliases: list[AreaAliasOut] = []
    cantidad_facturas: int = 0


class AreaCreate(BaseModel):
    nombre_normalizado: str


class AreaUpdate(BaseModel):
    nombre_normalizado: Optional[str] = None
