"""
Aprobacion/rechazo de facturas en staging (sección 5, pasos 9-12 del diseño),
con dos niveles de granularidad:

- Por fila individual (approve_staging_row / reject_staging_row): la forma
  principal de trabajar. Si una factura de las 200 que trae un archivo esta
  mal, se rechaza esa sola -- no hace falta tocar el resto.
- Por lote completo (approve_pending_in_batch / reject_pending_in_batch):
  un atajo que aplica la misma logica a todas las filas que todavia estan
  'pendiente' dentro de un batch, para no tener que aprobar de a una cuando
  la gran mayoria esta bien.

El estado del import_batch se recalcula despues de cada accion (individual o
de lote) en base al estado de sus filas -- no es un estado que se setea a mano.
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


def _crear_invoice_desde_staging(db: Session, staging: StagingInvoice, batch: ImportBatch, user_id: int) -> Invoice:
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
    db.flush()  # uno por uno: evita el bug de insertmanyvalues con lotes grandes (ver docs/decisiones-arquitectura.md)
    return invoice


def recompute_batch_estado(batch: ImportBatch) -> None:
    """
    El estado del lote se deriva de las decisiones tomadas fila por fila,
    no se setea a mano. Mientras queden filas 'pendiente', el lote sigue en
    revision. Cuando ya no queda ninguna pendiente, el lote pasa a 'aprobado'
    (si se aprobo al menos una factura) o 'rechazado' (si se rechazaron todas).
    """
    filas = batch.staging_invoices
    if not filas:
        return

    pendientes = [f for f in filas if f.resultado == "pendiente"]
    if pendientes:
        tiene_error_pendiente = any(f.estado_fila == "error" for f in pendientes)
        batch.estado = "con_errores" if tiene_error_pendiente else "pendiente_validacion"
        return

    aprobadas = [f for f in filas if f.resultado == "aprobada"]
    batch.estado = "aprobado" if aprobadas else "rechazado"


def approve_staging_row(db: Session, staging: StagingInvoice, user_id: int) -> Invoice:
    if staging.resultado != "pendiente":
        raise ValueError(f"Esta fila ya fue procesada (resultado actual: '{staging.resultado}')")

    batch = staging.import_batch
    invoice = _crear_invoice_desde_staging(db, staging, batch, user_id)

    staging.resultado = "aprobada"
    staging.invoice_id = invoice.id
    staging.procesado_por_id = user_id
    staging.procesado_en = datetime.utcnow()

    recompute_batch_estado(batch)

    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="aprobar_factura",
        entidad="staging_invoice",
        entidad_id=staging.id,
        valor_nuevo_json={"invoice_id": invoice.id},
        import_batch_id=batch.id,
    ))
    db.commit()
    return invoice


def reject_staging_row(db: Session, staging: StagingInvoice, user_id: int, motivo: str | None) -> None:
    if staging.resultado != "pendiente":
        raise ValueError(f"Esta fila ya fue procesada (resultado actual: '{staging.resultado}')")

    batch = staging.import_batch
    staging.resultado = "rechazada"
    staging.motivo_rechazo = motivo
    staging.procesado_por_id = user_id
    staging.procesado_en = datetime.utcnow()

    recompute_batch_estado(batch)

    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="rechazar_factura",
        entidad="staging_invoice",
        entidad_id=staging.id,
        motivo=motivo,
        import_batch_id=batch.id,
    ))
    db.commit()


def approve_pending_in_batch(db: Session, batch: ImportBatch, user_id: int, incluir_con_error: bool = False) -> dict:
    """
    Atajo de lote: aprueba todas las filas que todavia estan 'pendiente'.
    Por default deja afuera (sin tocar) las filas clasificadas como 'error'
    bloqueante, para que se revisen a mano; incluir_con_error=True las fuerza tambien.
    """
    aprobadas = 0
    omitidas_por_error = 0

    for staging in batch.staging_invoices:
        if staging.resultado != "pendiente":
            continue
        if staging.estado_fila == "error" and not incluir_con_error:
            omitidas_por_error += 1
            continue
        approve_staging_row(db, staging, user_id)
        aprobadas += 1

    return {"filas_aprobadas": aprobadas, "filas_excluidas_por_error": omitidas_por_error}


def reject_pending_in_batch(db: Session, batch: ImportBatch, user_id: int, motivo: str | None) -> dict:
    """Atajo de lote: rechaza todas las filas que todavia estan 'pendiente'."""
    rechazadas = 0
    for staging in batch.staging_invoices:
        if staging.resultado != "pendiente":
            continue
        reject_staging_row(db, staging, user_id, motivo)
        rechazadas += 1
    return {"filas_rechazadas": rechazadas}
