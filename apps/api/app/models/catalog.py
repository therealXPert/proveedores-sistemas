from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class Provider(Base, TimestampMixin, SoftDeleteMixin):
    """Proveedor normalizado. Los alias (nombres tal como llegan en el CSV) viven en provider_aliases."""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    nombre_normalizado = Column(String(255), nullable=False)
    razon_social = Column(String(255), nullable=True)
    cuit = Column(String(20), nullable=True, index=True)
    categoria_principal_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    moneda_habitual = Column(String(10), nullable=True, default="ARS")
    condiciones_comerciales = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)

    aliases = relationship("ProviderAlias", back_populates="provider", cascade="all, delete-orphan")
    categoria_principal = relationship("ExpenseCategory")


class ProviderAlias(Base, TimestampMixin):
    """Nombres con los que este proveedor aparece en los CSV de TSDocs (ej. 'Google', 'Google Cloud')."""
    __tablename__ = "provider_aliases"

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    alias_texto = Column(String(255), nullable=False, unique=True, index=True)

    provider = relationship("Provider", back_populates="aliases")


class ExpenseCategory(Base, TimestampMixin, SoftDeleteMixin):
    """
    Categoria de gasto. Auto-referenciada para soportar categoria/subcategoria.
    Seed inicial tomado de los codigos reales de 'Cuenta Personal' (ver docs/decisiones-arquitectura.md):
    Sueldos, Viaticos y Gastos al Personal, Otros Servicios, Data Center, Desarrollo de Software,
    Equipos de Computacion, Licencias, Telefonia y Comunicaciones, y sus variantes "Sistemas Inversiones".
    """
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    categoria_padre_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    codigo_erp = Column(String(20), nullable=True, index=True)  # ej. ST07, STI05 (viene de Cuenta Personal)

    subcategorias = relationship("ExpenseCategory", remote_side=[id])


class Area(Base, TimestampMixin, SoftDeleteMixin):
    """
    Sub-area de Sistemas (dimension de la columna 'Area' del CSV de TSDocs).
    Seed: Sistemas Aplicaciones Negocio, Sistemas Mesa de Servicio, Sistemas Tecnologia y Operaciones.
    El gasto de Seguridad se imputa dentro de "Sistemas Mesa de Servicio" (no es un area separada).
    """
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True)
    nombre_normalizado = Column(String(150), nullable=False, unique=True)

    aliases = relationship("AreaAlias", back_populates="area", cascade="all, delete-orphan")


class AreaAlias(Base, TimestampMixin):
    __tablename__ = "area_aliases"

    id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    alias_texto = Column(String(150), nullable=False, unique=True)

    area = relationship("Area", back_populates="aliases")


class CostCenter(Base, TimestampMixin, SoftDeleteMixin):
    """
    Centro de costo ERP: viene del codigo de 'Cuenta Personal' (ej. ST07, STI05).
    Catalogo propio, sin integracion automatica con el ERP en el MVP.
    """
    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), nullable=False, unique=True)  # ST01..ST08, STI03, STI05, STI06
    nombre = Column(String(150), nullable=False)


class BusinessUnit(Base, TimestampMixin, SoftDeleteMixin):
    """
    Unidad de Negocio beneficiaria del gasto (puede diferir de quien gestiona la compra).
    Seed real observado en Presupuesto_Sistemas.xlsx: Sistemas, Comercial, Marketing, RRHH,
    Adm & Fin, Logistica, Seguridad, Contact Center, Gestoria.
    """
    __tablename__ = "business_units"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False, unique=True)


class Company(Base, TimestampMixin, SoftDeleteMixin):
    """Empresa/razon social del grupo que factura el gasto (columna 'Empresa' del CSV: TAGLE, NIX, MOTCOR, etc.)."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False, unique=True)


class Branch(Base, TimestampMixin, SoftDeleteMixin):
    """Sucursal/sede (columna 'Sucursal' del CSV: Cordoba, San Luis, Rio IV, etc.)."""
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False, unique=True)


class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    codigo = Column(String(50), nullable=True, unique=True)
