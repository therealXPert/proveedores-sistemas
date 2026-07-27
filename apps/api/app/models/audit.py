from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSON().with_variant(JSONB, "postgresql")
from sqlalchemy.orm import relationship

from app.db import Base


class AuditEvent(Base):
    """
    Auditoria inmutable (sección 16 del diseño). No tiene updated_at a proposito:
    una vez creado un evento de auditoria, nunca se modifica.
    """
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha = Column(DateTime, nullable=False, index=True)
    accion = Column(String(100), nullable=False, index=True)  # ej. "aprobar_carga", "cambiar_proveedor"
    entidad = Column(String(100), nullable=False, index=True)  # ej. "invoice", "provider"
    entidad_id = Column(Integer, nullable=True, index=True)
    valor_anterior_json = Column(JSONType, nullable=True)
    valor_nuevo_json = Column(JSONType, nullable=True)
    ip_address = Column(String(50), nullable=True)
    motivo = Column(Text, nullable=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)

    user = relationship("User")
