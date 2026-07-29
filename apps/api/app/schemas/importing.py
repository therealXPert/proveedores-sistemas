from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValidationErrorOut(BaseModel):
    tipo: str
    severidad: str
    mensaje: str

    class Config:
        from_attributes = True


class StagingInvoiceOut(BaseModel):
    id: int
    estado_fila: str
    resultado: str
    invoice_id: Optional[int] = None
    motivo_rechazo: Optional[str] = None
    datos_mapeados: dict[str, Any] = Field(validation_alias="datos_mapeados_json")
    errores: list[ValidationErrorOut]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("datos_mapeados", mode="before")
    @classmethod
    def _default_empty(cls, v):
        return v or {}


class RejectRowRequest(BaseModel):
    motivo: Optional[str] = None


class ApproveRowResponse(BaseModel):
    staging_id: int
    invoice_id: int
    resultado: str = "aprobada"


class ImportBatchSummary(BaseModel):
    validos: int
    advertencias: int
    invalidos: int
    duplicados: int
    total_filas: int
    columnas_desconocidas: list[str]
    encoding_detectado: Optional[str] = None
    separador_detectado: Optional[str] = None


class ImportBatchOut(BaseModel):
    id: int
    estado: str
    resumen: Optional[ImportBatchSummary] = Field(default=None, validation_alias="resumen_json")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ApproveBatchResponse(BaseModel):
    filas_aprobadas: int
    filas_excluidas_por_error: int


class RejectBatchRequest(BaseModel):
    motivo: Optional[str] = None
