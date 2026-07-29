from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSON().with_variant(JSONB, "postgresql")
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.base import TimestampMixin


class ImportTemplate(Base, TimestampMixin):
    """Plantilla de mapeo de columnas CSV -> campos internos. Se versiona porque TSDocs puede cambiar su formato."""
    __tablename__ = "import_templates"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    origen = Column(String(50), default="TSDocs", nullable=False)

    versiones = relationship("ImportTemplateVersion", back_populates="template", cascade="all, delete-orphan")


class ImportTemplateVersion(Base, TimestampMixin):
    __tablename__ = "import_template_versions"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("import_templates.id"), nullable=False)
    version = Column(Integer, nullable=False)
    mapeo_json = Column(JSONType, nullable=False)  # {"columna_csv": "campo_interno", ...}
    formato_fecha = Column(String(50), nullable=True)  # ej. "%d/%m/%Y"
    separador_decimal = Column(String(5), nullable=True)  # "," o "."
    vigente_desde = Column(DateTime, nullable=True)

    template = relationship("ImportTemplate", back_populates="versiones")


class ImportFile(Base, TimestampMixin):
    """Archivo original subido, con su copia en Cloud Storage."""
    __tablename__ = "import_files"

    id = Column(Integer, primary_key=True)
    nombre_original = Column(String(255), nullable=False)
    gcs_path = Column(String(500), nullable=False)
    hash_archivo = Column(String(64), nullable=True, index=True)  # sha256, para detectar re-subidas del mismo archivo
    subido_por_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    batches = relationship("ImportBatch", back_populates="import_file")


class ImportBatch(Base, TimestampMixin):
    """
    Una 'carga': un archivo procesado con una plantilla. Estados segun sección 5 del diseño:
    recibido, procesando, pendiente_validacion, con_errores, validado, aprobado, rechazado, anulado.
    """
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True)
    import_file_id = Column(Integer, ForeignKey("import_files.id"), nullable=False)
    template_version_id = Column(Integer, ForeignKey("import_template_versions.id"), nullable=True)
    estado = Column(String(30), nullable=False, default="recibido")
    resumen_json = Column(JSONType, nullable=True)  # {validos, advertencias, invalidos, duplicados, totales}
    aprobado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_aprobacion = Column(DateTime, nullable=True)

    import_file = relationship("ImportFile", back_populates="batches")
    staging_invoices = relationship("StagingInvoice", back_populates="import_batch", cascade="all, delete-orphan")


class StagingInvoice(Base, TimestampMixin):
    """
    Fila cruda + mapeada de un CSV, antes de convertirse en Invoice definitiva.

    Dos campos de estado con significados distintos, a proposito:
    - estado_fila: clasificacion de VALIDACION (valida/advertencia/error), se calcula
      una sola vez al importar y no cambia despues.
    - resultado: DECISION del usuario sobre esta fila puntual (pendiente/aprobada/
      rechazada). Permite aprobar o rechazar factura por factura, no solo el lote
      completo -- si una fila esta mal, no hace falta rechazar todo el archivo.
    """
    __tablename__ = "staging_invoices"

    id = Column(Integer, primary_key=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    datos_crudos_json = Column(JSONType, nullable=False)  # la fila del CSV tal cual vino
    datos_mapeados_json = Column(JSONType, nullable=True)  # ya mapeada a campos internos, editable durante validacion
    estado_fila = Column(String(30), nullable=False, default="pendiente")  # valida/advertencia/error
    resultado = Column(String(20), nullable=False, default="pendiente")  # pendiente/aprobada/rechazada
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)  # factura generada, si se aprobo
    motivo_rechazo = Column(Text, nullable=True)
    procesado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    procesado_en = Column(DateTime, nullable=True)
    es_duplicado_de_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    motivo_cambio_categoria = Column(Text, nullable=True)  # comentario opcional si se cambio la categoria propuesta

    import_batch = relationship("ImportBatch", back_populates="staging_invoices")
    errores = relationship("ValidationError", back_populates="staging_invoice", cascade="all, delete-orphan")


class ValidationError(Base, TimestampMixin):
    __tablename__ = "validation_errors"

    id = Column(Integer, primary_key=True)
    staging_invoice_id = Column(Integer, ForeignKey("staging_invoices.id"), nullable=False)
    tipo = Column(String(100), nullable=False)  # ej. "importe_invalido", "proveedor_inexistente"
    severidad = Column(String(20), nullable=False)  # bloqueante / advertencia / info
    mensaje = Column(Text, nullable=False)
    aceptado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    justificacion = Column(Text, nullable=True)

    staging_invoice = relationship("StagingInvoice", back_populates="errores")


class ValidationRule(Base, TimestampMixin):
    __tablename__ = "validation_rules"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    tipo = Column(String(50), nullable=False)  # ej. "clasificacion_automatica", "duplicado"
    condicion_json = Column(JSONType, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)
