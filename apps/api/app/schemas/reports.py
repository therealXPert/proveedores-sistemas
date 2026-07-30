from typing import Optional

from pydantic import BaseModel


class DashboardKPIs(BaseModel):
    anio: int
    mes: int
    gasto_total_mes: float
    gasto_acumulado_anio: float
    presupuesto_mensual: float
    presupuesto_anual: float
    porcentaje_consumido_mes: Optional[float] = None
    desvio_contra_presupuesto_mes: float
    proyeccion_cierre_anio: Optional[float] = None
    variacion_mes_anterior_pct: Optional[float] = None
    variacion_interanual_pct: Optional[float] = None
    cantidad_facturas_mes: int
    cantidad_proveedores_mes: int
    importaciones_pendientes: int
    registros_con_error: int


class EvolucionMensualItem(BaseModel):
    mes: int
    gasto: float


class RankingProveedorItem(BaseModel):
    provider_id: int
    nombre: str
    monto: float
    participacion_pct: float
    acumulado_pct: float


class RankingCategoriaItem(BaseModel):
    category_id: int
    nombre: str
    monto: float
    participacion_pct: float
    acumulado_pct: float


class RankingAreaItem(BaseModel):
    area_id: int
    nombre: str
    monto: float
    participacion_pct: float
    acumulado_pct: float


class InvoiceListItem(BaseModel):
    id: int
    numero_factura: Optional[str] = None
    tipo_documento: str
    fecha_emision: str
    provider_nombre: Optional[str] = None
    area_nombre: Optional[str] = None
    category_nombre: Optional[str] = None
    importe_total: float
    moneda: str
    descripcion: Optional[str] = None
    usuario_aprobador_nombre: Optional[str] = None
    import_batch_id: Optional[int] = None
    link_documento_original: Optional[str] = None
