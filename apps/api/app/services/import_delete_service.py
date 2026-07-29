"""
Borrado fisico de una importacion (ver nota importante en app/api/imports.py:
esto NO es lo que describe la sección 5 del diseño ("nunca borrar fisicamente,
usar anulacion logica") -- se implementa asi por pedido explicito para poder
deshacer pruebas sin editar la base a mano. Si esto pasa a produccion real,
conviene reemplazarlo por una anulacion que preserve trazabilidad contable.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.importing import ImportBatch, StagingInvoice, ValidationError
from app.models.invoicing import Invoice
from app.models.audit import AuditEvent


def delete_import_batch(db: Session, batch: ImportBatch, user_id: int) -> dict:
    invoice_ids = [row[0] for row in db.query(Invoice.id).filter(Invoice.import_batch_id == batch.id).all()]
    facturas_asociadas = len(invoice_ids)

    if invoice_ids:
        # Otras filas de staging (de este u otros batches) pueden referenciar estas
        # facturas via invoice_id o es_duplicado_de_invoice_id -- hay que desvincularlas
        # antes de borrar, o la base rechaza el delete por violacion de foreign key.
        filas_marcadas_duplicado = [
            row[0] for row in db.query(StagingInvoice.id)
            .filter(StagingInvoice.es_duplicado_de_invoice_id.in_(invoice_ids))
            .all()
        ]

        db.query(StagingInvoice).filter(StagingInvoice.invoice_id.in_(invoice_ids)).update(
            {"invoice_id": None}, synchronize_session=False
        )
        db.query(StagingInvoice).filter(StagingInvoice.es_duplicado_de_invoice_id.in_(invoice_ids)).update(
            {"es_duplicado_de_invoice_id": None}, synchronize_session=False
        )
        db.query(Invoice).filter(Invoice.id.in_(invoice_ids)).delete(synchronize_session=False)

        if filas_marcadas_duplicado:
            # El error de "duplicado contra aprobadas" queda obsoleto (la factura
            # original ya no existe): se borra y se recalcula el estado de esas filas.
            db.query(ValidationError).filter(
                ValidationError.staging_invoice_id.in_(filas_marcadas_duplicado),
                ValidationError.tipo == "duplicado_factura_existente",
            ).delete(synchronize_session=False)

            for fila in db.query(StagingInvoice).filter(StagingInvoice.id.in_(filas_marcadas_duplicado)).all():
                severidades = {e.severidad for e in fila.errores}
                if "bloqueante" in severidades:
                    fila.estado_fila = "error"
                elif "advertencia" in severidades:
                    fila.estado_fila = "advertencia"
                else:
                    fila.estado_fila = "valida"

    import_file = batch.import_file

    # La auditoria es inmutable (sección 16 del diseño): no se borran los eventos,
    # solo se les quita la referencia al batch que va a dejar de existir.
    db.query(AuditEvent).filter(AuditEvent.import_batch_id == batch.id).update(
        {"import_batch_id": None}, synchronize_session=False
    )

    estado_original = batch.estado
    batch_id = batch.id

    db.delete(batch)  # cascada de ORM: borra sus staging_invoices -> validation_errors
    if import_file:
        db.delete(import_file)

    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="eliminar_importacion",
        entidad="import_batch",
        entidad_id=batch_id,
        valor_anterior_json={"estado": estado_original, "facturas_aprobadas_eliminadas": facturas_asociadas},
    ))
    db.commit()
    return {"eliminado": True, "facturas_eliminadas": facturas_asociadas}
