"""
Administracion de proveedores (sección 8 del diseño): edicion retroactiva y
fusion de duplicados. Al fusionar, TODO lo que referencia al proveedor
descartado se reasigna al proveedor final antes de borrarlo (facturas, alias,
presupuestos) -- no se pierde nada, y queda auditado.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.catalog import Provider, ProviderAlias
from app.models.invoicing import Invoice
from app.models.budget import Budget
from app.models.audit import AuditEvent


def merge_providers(db: Session, target: Provider, other: Provider, user_id: int) -> dict:
    if target.id == other.id:
        raise ValueError("No se puede fusionar un proveedor consigo mismo")

    facturas_reasignadas = db.query(Invoice).filter(Invoice.provider_id == other.id).update(
        {"provider_id": target.id}, synchronize_session=False
    )
    alias_reasignados = db.query(ProviderAlias).filter(ProviderAlias.provider_id == other.id).update(
        {"provider_id": target.id}, synchronize_session=False
    )
    presupuestos_reasignados = db.query(Budget).filter(Budget.provider_id == other.id).update(
        {"provider_id": target.id}, synchronize_session=False
    )

    # El proveedor descartado tambien queda como alias del final, por si su nombre
    # original aparece de nuevo en un CSV futuro.
    existe_alias = db.query(ProviderAlias).filter(ProviderAlias.alias_texto == other.nombre_normalizado).first()
    if not existe_alias:
        db.add(ProviderAlias(provider_id=target.id, alias_texto=other.nombre_normalizado))

    nombre_descartado = other.nombre_normalizado
    other_id = other.id
    db.delete(other)

    db.add(AuditEvent(
        user_id=user_id,
        fecha=datetime.utcnow(),
        accion="fusionar_proveedores",
        entidad="provider",
        entidad_id=target.id,
        valor_anterior_json={"proveedor_descartado_id": other_id, "proveedor_descartado_nombre": nombre_descartado},
        valor_nuevo_json={
            "facturas_reasignadas": facturas_reasignadas,
            "alias_reasignados": alias_reasignados,
            "presupuestos_reasignados": presupuestos_reasignados,
        },
    ))
    db.commit()

    return {
        "facturas_reasignadas": facturas_reasignadas,
        "alias_reasignados": alias_reasignados,
        "presupuestos_reasignados": presupuestos_reasignados,
    }
