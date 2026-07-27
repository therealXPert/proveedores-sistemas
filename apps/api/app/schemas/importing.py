from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ValidationErrorOut(BaseModel):
    tipo: str
    severidad: str
    mensaje: str

    class Config:
        from_attributes = True


class StagingInvoiceOut(BaseModel):
    id: int
    estado_fila: str
    datos_mapeados: dict[str, Any]
    errores: list[ValidationErrorOut]

    class Config:
        from_attributes = True


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
