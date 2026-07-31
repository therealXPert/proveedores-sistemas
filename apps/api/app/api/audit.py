"""Consulta de auditoria (sección 16 del diseño). Es de solo lectura: nunca se edita ni se borra un evento."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.deps import require_role
from app.models.security import User
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_audit_events(
    accion: str | None = None,
    entidad: str | None = None,
    usuario_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Administrador")),
):
    q = db.query(AuditEvent)
    if accion:
        q = q.filter(AuditEvent.accion == accion)
    if entidad:
        q = q.filter(AuditEvent.entidad == entidad)
    if usuario_id:
        q = q.filter(AuditEvent.user_id == usuario_id)
    if desde:
        q = q.filter(AuditEvent.fecha >= desde)
    if hasta:
        q = q.filter(AuditEvent.fecha <= hasta)

    rows = q.order_by(AuditEvent.fecha.desc()).limit(limit).all()

    resultado = []
    for e in rows:
        resultado.append({
            "id": e.id,
            "fecha": e.fecha,
            "usuario_nombre": e.user.nombre if e.user else None,
            "usuario_email": e.user.email if e.user else None,
            "accion": e.accion,
            "entidad": e.entidad,
            "entidad_id": e.entidad_id,
            "valor_anterior": e.valor_anterior_json,
            "valor_nuevo": e.valor_nuevo_json,
            "motivo": e.motivo,
            "ip_address": e.ip_address,
            "import_batch_id": e.import_batch_id,
        })
    return resultado


@router.get("/acciones", response_model=list[str])
def list_acciones_distintas(db: Session = Depends(get_db), current_user: User = Depends(require_role("Administrador"))):
    """Lista de valores distintos de 'accion' ya registrados, para armar el filtro en la UI."""
    rows = db.query(AuditEvent.accion).distinct().order_by(AuditEvent.accion).all()
    return [r[0] for r in rows]


@router.get("/entidades", response_model=list[str])
def list_entidades_distintas(db: Session = Depends(get_db), current_user: User = Depends(require_role("Administrador"))):
    """Lista de valores distintos de 'entidad' ya registrados, para armar el filtro en la UI."""
    rows = db.query(AuditEvent.entidad).distinct().order_by(AuditEvent.entidad).all()
    return [r[0] for r in rows]
