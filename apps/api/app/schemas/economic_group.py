from typing import Optional

from pydantic import BaseModel


class EconomicGroupOut(BaseModel):
    id: int
    nombre: str
    is_active: bool
    cantidad_empresas: int = 0


class EconomicGroupCreate(BaseModel):
    nombre: str


class EconomicGroupUpdate(BaseModel):
    nombre: Optional[str] = None


class CompanyOut(BaseModel):
    id: int
    nombre: str
    economic_group_id: Optional[int] = None
    economic_group_nombre: Optional[str] = None
    cantidad_facturas: int = 0


class CompanyUpdate(BaseModel):
    economic_group_id: Optional[int] = None
