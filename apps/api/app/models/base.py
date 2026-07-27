"""
Mixins reutilizables para todos los modelos.
Se usan IDs enteros autoincrementales (mas simples de leer/depurar que UUID
para un equipo chico); si mas adelante se necesita exponer IDs publicamente
sin que sean secuenciales, se puede agregar un campo 'public_id' (UUID) aparte.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Boolean


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Baja logica: nunca se borra fisicamente, se marca is_active=False."""
    is_active = Column(Boolean, default=True, nullable=False)
