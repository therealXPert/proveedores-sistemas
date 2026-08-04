from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Numeric
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.base import TimestampMixin


class Invoice(Base, TimestampMixin):
    """
    Factura ya aprobada (post-staging). Nunca se borra fisicamente: una anulacion
    se marca en 'estado', no se elimina la fila (trazabilidad, sección 5 y 19 del diseño).
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True, index=True)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True, index=True)
    business_unit_id = Column(Integer, ForeignKey("business_units.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    economic_group_id = Column(Integer, ForeignKey("economic_groups.id"), nullable=True, index=True)
    # ^ Se autocompleta con el grupo de la empresa (company_id) al aprobar la factura,
    # pero se puede sobreescribir a mano (por fila o en bloque para todo un archivo) --
    # es el "modelo hibrido" pedido: reportes de TSDocs que mezclan empresas de mas de
    # un grupo economico necesitan permitir la correccion manual, no solo la automatica.
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    numero_factura = Column(String(50), nullable=True, index=True)
    tipo_documento = Column(String(50), nullable=False, default="Factura")  # Factura/Nota Debito/Nota Credito/Fact.Cred.Pyme
    letra_arca = Column(String(5), nullable=True)
    fecha_emision = Column(DateTime, nullable=False, index=True)
    fecha_vencimiento = Column(DateTime, nullable=True)

    descripcion = Column(Text, nullable=True)  # NUNCA truncar (sección 5, dato clave para clasificar)

    importe_neto = Column(Numeric(14, 2), nullable=True)
    impuestos = Column(Numeric(14, 2), nullable=True)
    importe_total = Column(Numeric(14, 2), nullable=False)
    moneda = Column(String(10), nullable=False, default="ARS")
    tasa_cambio = Column(Numeric(10, 4), nullable=True)  # tal cual viene en la columna 'Tasa' del CSV
    importe_en_dolares = Column(Numeric(14, 2), nullable=True)

    orden_compra = Column(String(50), nullable=True)
    estado = Column(String(30), nullable=False, default="aprobado")  # aprobado / anulado
    cae = Column(String(30), nullable=True)
    identificador_externo_tsdocs = Column(String(50), nullable=True, index=True)  # Id Documento del CSV
    link_documento_original = Column(String(500), nullable=True)

    usuario_aprobador_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    observaciones = Column(Text, nullable=True)

    provider = relationship("Provider")
    area = relationship("Area")
    category = relationship("ExpenseCategory")
    cost_center = relationship("CostCenter")
    business_unit = relationship("BusinessUnit")
    company = relationship("Company")
    branch = relationship("Branch")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base, TimestampMixin):
    """Detalle por concepto, solo si el CSV llega a traerlo (no es el caso del CSV real de TSDocs analizado)."""
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    descripcion_item = Column(Text, nullable=True)
    importe = Column(Numeric(14, 2), nullable=True)

    invoice = relationship("Invoice", back_populates="lines")
