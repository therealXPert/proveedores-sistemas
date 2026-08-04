"""
Edicion de una factura en staging antes de aprobarla (sección 5, punto 9 del
diseño: "el usuario puede corregir, excluir o aceptar registros"). Al editar,
se recalculan las validaciones (incluido el chequeo de duplicado contra
facturas ya aprobadas) con los valores nuevos -- por ejemplo, si el numero de
factura estaba mal tipeado y por eso disparaba un falso duplicado, corregirlo
aca saca esa advertencia.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.importing import StagingInvoice, ValidationError
from app.models.audit import AuditEvent
from app.services import validation
from app.services.parsing import parse_fecha, parse_importe
from app.services.json_utils import to_json_safe

EDITABLE_FIELDS = {
    "numero_factura",
    "fecha_emision",
    "importe_total",
    "moneda",
    "tipo_documento",
    "descripcion",
    "orden_compra",
    "observaciones",
    "provider_id",
    "area_id",
    "category_id",
    "cost_center_id",
    "business_unit_id",
    "company_id",
    "branch_id",
    "economic_group_id",
}


def update_staging_row(db: Session, staging: StagingInvoice, updates: dict, user_id: int) -> StagingInvoice:
    if staging.resultado != "pendiente":
        raise ValueError(
            f"No se puede editar esta factura: ya fue procesada (resultado actual: '{staging.resultado}')"
        )

    mapped = dict(staging.datos_mapeados_json or {})
    valor_anterior = dict(mapped)

    for campo, valor in updates.items():
        if campo not in EDITABLE_FIELDS:
            continue
        if campo == "fecha_emision" and valor:
            parsed = parse_fecha(valor)
            mapped[campo] = parsed.isoformat() if parsed else None
        elif campo == "importe_total":
            parsed = parse_importe(valor) if valor is not None else None
            mapped[campo] = str(parsed) if parsed is not None else None
        else:
            mapped[campo] = valor

    # Re-validar con los valores ya editados (importe como Decimal, tal como espera validar_fila)
    mapped_para_validar = dict(mapped)
    mapped_para_validar["importe_total"] = parse_importe(mapped.get("importe_total"))

    provider_encontrado = mapped.get("provider_id") is not None
    errores = validation.validar_fila(mapped_para_validar, provider_encontrado=provider_encontrado)

    duplicado_invoice = validation.detectar_duplicado_contra_aprobadas(
        db, mapped.get("provider_id"), mapped_para_validar
    )
    if duplicado_invoice:
        errores.append((
            "duplicado_factura_existente",
            "bloqueante",
            f"Ya existe la factura aprobada #{duplicado_invoice.id} con el mismo proveedor/numero/importe",
        ))
    staging.es_duplicado_de_invoice_id = duplicado_invoice.id if duplicado_invoice else None

    # Se recalculan todos los errores de validacion desde cero (incluye duplicado contra aprobadas).
    # El chequeo de "duplicado dentro del mismo archivo" no se vuelve a correr aca porque requeriria
    # recorrer de nuevo todo el batch; si eso era el unico problema de la fila, el usuario puede
    # simplemente aprobarla despues de revisarla a mano.
    for e in list(staging.errores):
        db.delete(e)
    for tipo, severidad, mensaje in errores:
        db.add(ValidationError(staging_invoice_id=staging.id, tipo=tipo, severidad=severidad, mensaje=mensaje))

    severidades = {sev for _, sev, _ in errores}
    if "bloqueante" in severidades:
        staging.estado_fila = "error"
    elif "advertencia" in severidades:
        staging.estado_fila = "advertencia"
    else:
        staging.estado_fila = "valida"

    staging.datos_mapeados_json = to_json_safe(mapped)

    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="editar_factura_staging",
        entidad="staging_invoice",
        entidad_id=staging.id,
        valor_anterior_json=to_json_safe(valor_anterior),
        valor_nuevo_json=to_json_safe(mapped),
        import_batch_id=staging.import_batch_id,
    ))

    db.commit()
    return staging
