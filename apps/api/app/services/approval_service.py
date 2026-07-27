"""
Aprobacion/rechazo de una carga (sección 5, pasos 9-12 del diseño).
Solo las filas en estado 'valida' o 'advertencia' pasan a ser Invoice definitivas;
las que quedaron en 'error' se excluyen automaticamente (hay que corregirlas en una
proxima carga, o mas adelante agregar edicion in-place de staging antes de aprobar).
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.importing import ImportBatch, StagingInvoice
from app.models.invoicing import Invoice
from app.models.audit import AuditEvent


def _decimal_or_none(value):
    if value is None:
        return None
    return Decimal(str(value))


def _datetime_or_none(value):
    if value is None:
        return None
    return datetime.fromisoformat(value)


def approve_batch(db: Session, batch: ImportBatch, user_id: int) -> dict:
    filas_aprobadas = 0
    filas_excluidas_por_error = 0

    for staging in batch.staging_invoices:
        if staging.estado_fila == "error":
            filas_excluidas_por_error += 1
            continue
        if staging.estado_fila == "excluida":
            continue

        m = staging.datos_mapeados_json

        invoice = Invoice(
            import_batch_id=batch.id,
            provider_id=m.get("provider_id"),
            area_id=m.get("area_id"),
            category_id=m.get("category_id"),
            cost_center_id=m.get("cost_center_id"),
            company_id=m.get("company_id"),
            branch_id=m.get("branch_id"),
            numero_factura=m.get("numero_factura"),
            tipo_documento=m.get("tipo_documento") or "Factura",
            letra_arca=m.get("letra_arca"),
            fecha_emision=_datetime_or_none(m.get("fecha_emision")),
            fecha_vencimiento=_datetime_or_none(m.get("fecha_vencimiento")),
            descripcion=m.get("descripcion"),
            importe_neto=_decimal_or_none(m.get("importe_neto")),
            importe_total=_decimal_or_none(m.get("importe_total")),
            moneda=m.get("moneda") or "ARS",
            tasa_cambio=_decimal_or_none(m.get("tasa_cambio")),
            importe_en_dolares=_decimal_or_none(m.get("importe_en_dolares")),
            orden_compra=m.get("orden_compra"),
            estado="aprobado",
            cae=m.get("cae"),
            identificador_externo_tsdocs=m.get("identificador_externo_tsdocs"),
            link_documento_original=m.get("link_documento_original"),
            usuario_aprobador_id=user_id,
            observaciones=m.get("observaciones"),
        )
        db.add(invoice)
        db.flush()  # uno por uno: evita un bug de SQLAlchemy con INSERT masivo en lotes grandes (ver docs/decisiones-arquitectura.md)
        filas_aprobadas += 1

    batch.estado = "aprobado"
    batch.aprobado_por_id = user_id
    batch.fecha_aprobacion = datetime.utcnow()

    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="aprobar_carga",
        entidad="import_batch",
        entidad_id=batch.id,
        valor_nuevo_json={"filas_aprobadas": filas_aprobadas, "filas_excluidas_por_error": filas_excluidas_por_error},
        import_batch_id=batch.id,
    ))

    db.commit()
    return {"filas_aprobadas": filas_aprobadas, "filas_excluidas_por_error": filas_excluidas_por_error}


def reject_batch(db: Session, batch: ImportBatch, user_id: int, motivo: str | None) -> None:
    batch.estado = "rechazado"
    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="rechazar_carga",
        entidad="import_batch",
        entidad_id=batch.id,
        motivo=motivo,
        import_batch_id=batch.id,
    ))
    db.commit()
