from typing import Optional

from pydantic import BaseModel


class BudgetOut(BaseModel):
    id: int
    anio: int
    mes: Optional[int] = None
    provider_id: Optional[int] = None
    provider_nombre: Optional[str] = None
    area_id: Optional[int] = None
    area_nombre: Optional[str] = None
    category_id: Optional[int] = None
    category_nombre: Optional[str] = None
    cost_center_id: Optional[int] = None
    cost_center_nombre: Optional[str] = None
    business_unit_id: Optional[int] = None
    business_unit_nombre: Optional[str] = None
    moneda: str
    periodicidad_original: Optional[str] = None
    importe_original: Optional[float] = None
    importe_mensual_equivalente: Optional[float] = None
    comentario: Optional[str] = None


class BudgetCreate(BaseModel):
    anio: int
    mes: Optional[int] = None
    provider_id: Optional[int] = None
    area_id: Optional[int] = None
    category_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    business_unit_id: Optional[int] = None
    moneda: str = "ARS"
    periodicidad_original: Optional[str] = "Mensual"
    importe_original: Optional[float] = None
    comentario: Optional[str] = None


class BudgetUpdate(BaseModel):
    provider_id: Optional[int] = None
    area_id: Optional[int] = None
    category_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    business_unit_id: Optional[int] = None
    periodicidad_original: Optional[str] = None
    importe_original: Optional[float] = None
    comentario: Optional[str] = None


class BudgetResumenItem(BaseModel):
    provider_id: int
    provider_nombre: str
    presupuesto_mensual: float
    gasto_real_promedio_mensual: float
    gasto_real_total: float
    desvio_mensual: float
