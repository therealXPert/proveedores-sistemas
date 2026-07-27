from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import get_current_user, require_role
from app.models.security import User
from app.models.importing import ImportBatch
from app.schemas.importing import (
    ImportBatchOut,
    StagingInvoiceOut,
    ApproveBatchResponse,
    RejectBatchRequest,
)
from app.services.import_service import process_uploaded_file
from app.services.approval_service import approve_batch, reject_batch

router = APIRouter(prefix="/imports", tags=["imports"])

TAMANO_MAXIMO_MB = 20
EXTENSIONES_PERMITIDAS = (".csv", ".xlsx", ".xls")


def _get_batch_or_404(db: Session, batch_id: int) -> ImportBatch:
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importacion no encontrada")
    return batch


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
    return [
        {
            "id": s.id,
            "estado_fila": s.estado_fila,
            "datos_mapeados": s.datos_mapeados_json or {},
            "errores": [
                {"tipo": e.tipo, "severidad": e.severidad, "mensaje": e.mensaje} for e in s.errores
            ],
        }
        for s in batch.staging_invoices
    ]


@router.post("/{batch_id}/approve", response_model=ApproveBatchResponse)
def approve(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    batch = _get_batch_or_404(db, batch_id)
    if batch.estado not in ("pendiente_validacion", "con_errores"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede aprobar una carga en estado '{batch.estado}'",
        )
    resultado = approve_batch(db, batch, current_user.id)
    return resultado


@router.post("/{batch_id}/reject")
def reject(
    batch_id: int,
    payload: RejectBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador", "Analista")),
):
    batch = _get_batch_or_404(db, batch_id)
    reject_batch(db, batch, current_user.id, payload.motivo)
    return {"estado": "rechazado"}
