from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Numeric
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.base import TimestampMixin


class BudgetVersion(Base, TimestampMixin):
    """Version de un conjunto de presupuestos: original, revisado, vigente (sección 10 del diseño)."""
    __tablename__ = "budget_versions"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    tipo = Column(String(20), nullable=False)  # original / revisado / vigente
    comentario = Column(Text, nullable=True)

    budgets = relationship("Budget", back_populates="version")


class Budget(Base, TimestampMixin):
    """
    Presupuesto por año/mes/proveedor/categoria/area/centro de costo/unidad de negocio/proyecto/moneda.
    Periodicidad real observada en Presupuesto_Sistemas.xlsx (Mensual/Bimensual/Trimestral/A demanda)
    se normaliza a un monto MENSUAL equivalente en 'importe_mensual_equivalente' (ver addendum #28
    del documento de diseño); 'periodicidad_original' e 'importe_original' quedan para trazabilidad.
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    budget_version_id = Column(Integer, ForeignKey("budget_versions.id"), nullable=False)

    anio = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=True, index=True)  # NULL = presupuesto anual sin distribuir por mes todavia

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True)
    business_unit_id = Column(Integer, ForeignKey("business_units.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    moneda = Column(String(10), nullable=False, default="ARS")
    periodicidad_original = Column(String(20), nullable=True)  # Mensual/Bimensual/Trimestral/A demanda
    importe_original = Column(Numeric(14, 2), nullable=True)
    importe_mensual_equivalente = Column(Numeric(14, 2), nullable=True)

    comentario = Column(Text, nullable=True)

    version = relationship("BudgetVersion", back_populates="budgets")
    provider = relationship("Provider")
