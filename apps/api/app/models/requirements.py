from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.base import TimestampMixin


class Requirement(Base, TimestampMixin):
    """Backlog basico de evolutivos (sección 17 del diseño)."""
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    solicitante_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prioridad = Column(String(20), nullable=True)  # baja/media/alta
    categoria = Column(String(100), nullable=True)
    estado = Column(String(30), nullable=False, default="propuesto")
    responsable_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version_objetivo = Column(String(50), nullable=True)

    solicitante = relationship("User", foreign_keys=[solicitante_id])
    responsable = relationship("User", foreign_keys=[responsable_id])
    comentarios = relationship("RequirementComment", back_populates="requirement", cascade="all, delete-orphan")


class RequirementComment(Base, TimestampMixin):
    __tablename__ = "requirement_comments"

    id = Column(Integer, primary_key=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    texto = Column(Text, nullable=False)

    requirement = relationship("Requirement", back_populates="comentarios")


class Attachment(Base, TimestampMixin):
    """Adjuntos genericos, reutilizable para requerimientos u otras entidades."""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    entidad = Column(String(100), nullable=False)  # ej. "requirement"
    entidad_id = Column(Integer, nullable=False)
    gcs_path = Column(String(500), nullable=False)
    nombre_original = Column(String(255), nullable=False)
