from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: int
    fecha: datetime
    usuario_nombre: Optional[str] = None
    usuario_email: Optional[str] = None
    accion: str
    entidad: str
    entidad_id: Optional[int] = None
    valor_anterior: Optional[dict[str, Any]] = None
    valor_nuevo: Optional[dict[str, Any]] = None
    motivo: Optional[str] = None
    ip_address: Optional[str] = None
    import_batch_id: Optional[int] = None
