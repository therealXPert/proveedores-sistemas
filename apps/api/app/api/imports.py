from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.importing import ImportBatch, StagingInvoice
from app.schemas.importing import (
    ImportBatchOut,
    StagingInvoiceOut,
    ApproveBatchResponse,
    RejectBatchRequest,
    RejectRowRequest,
    ApproveRowResponse,
    StagingRowUpdate,
)
from app.services.import_service import process_uploaded_file
from app.services.approval_service import (
    approve_pending_in_batch,
    reject_pending_in_batch,
    approve_staging_row,
    reject_staging_row,
)
from app.services.staging_edit_service import update_staging_row
from app.services.import_delete_service import delete_import_batch

router = APIRouter(prefix="/imports", tags=["imports"])

TAMANO_MAXIMO_MB = 20
EXTENSIONES_PERMITIDAS = (".csv", ".xlsx", ".xls")


def _get_batch_or_404(db: Session, batch_id: int) -> ImportBatch:
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importacion no encontrada")
    return batch


def _get_staging_or_404(db: Session, staging_id: int) -> StagingInvoice:
    staging = db.query(StagingInvoice).filter(StagingInvoice.id == staging_id).first()
    if not staging:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura en revisión no encontrada")
    return staging


@router.delete("/{batch_id}")
def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    """
    Borra fisicamente una importacion: la carga en si, sus filas de staging, y
    -- si ya estaba aprobada -- TAMBIEN las facturas que genero. Es un borrado
    real, sin trazabilidad (a diferencia de la "anulacion" que describe la
    sección 5 del diseño). Se implementa asi por pedido explicito para poder
    deshacer pruebas sin tener que editar la base a mano; en un uso productivo
    real conviene reemplazar esto por una anulacion logica que preserve
    auditoria contable.
    """
    batch = _get_batch_or_404(db, batch_id)
    return delete_import_batch(db, batch, current_user.id)


@router.post("/upload", response_model=ImportBatchOut)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    if not file.filename.lower().endswith(EXTENSIONES_PERMITIDAS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extension no permitida. Se aceptan: {', '.join(EXTENSIONES_PERMITIDAS)}",
        )

    content = await file.read()
    if len(content) > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo supera el tamaño maximo permitido ({TAMANO_MAXIMO_MB} MB)",
        )

    batch = process_uploaded_file(db, current_user.id, file.filename, content)
    return batch


@router.get("", response_model=list[ImportBatchOut])
def list_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ImportBatch).order_by(ImportBatch.id.desc()).all()


@router.get("/{batch_id}", response_model=ImportBatchOut)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_batch_or_404(db, batch_id)


@router.get("/{batch_id}/preview", response_model=list[StagingInvoiceOut])
def preview_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vista previa completa, con la descripcion sin truncar (sección 5 del diseño)."""
    batch = _get_batch_or_404(db, batch_id)
    return batch.staging_invoices


# --- Acciones por factura individual (la forma principal de trabajar) ---


@router.patch("/staging/{staging_id}", response_model=StagingInvoiceOut)
def update_row(
    staging_id: int,
    payload: StagingRowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    staging = _get_staging_or_404(db, staging_id)
    updates = payload.model_dump(exclude_unset=True)
    try:
        update_staging_row(db, staging, updates, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return staging


@router.post("/staging/{staging_id}/approve", response_model=ApproveRowResponse)
def approve_row(
    staging_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    staging = _get_staging_or_404(db, staging_id)
    try:
        invoice = approve_staging_row(db, staging, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ApproveRowResponse(staging_id=staging.id, invoice_id=invoice.id)


@router.post("/staging/{staging_id}/reject")
def reject_row(
    staging_id: int,
    payload: RejectRowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    staging = _get_staging_or_404(db, staging_id)
    try:
        reject_staging_row(db, staging, current_user.id, payload.motivo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"staging_id": staging.id, "resultado": "rechazada"}


# --- Atajos por lote: aplican la misma accion a todas las filas pendientes ---


@router.post("/{batch_id}/approve", response_model=ApproveBatchResponse)
def approve_batch_pending(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    batch = _get_batch_or_404(db, batch_id)
    if batch.estado not in ("pendiente_validacion", "con_errores"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No quedan facturas pendientes en esta carga (estado actual: '{batch.estado}')",
        )
    resultado = approve_pending_in_batch(db, batch, current_user.id)
    return resultado


@router.post("/{batch_id}/reject")
def reject_batch_pending(
    batch_id: int,
    payload: RejectBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    batch = _get_batch_or_404(db, batch_id)
    resultado = reject_pending_in_batch(db, batch, current_user.id, payload.motivo)
    return resultado
