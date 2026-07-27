"""
Normalizacion de proveedores (sección 8 del diseño): un mismo proveedor puede
aparecer con distintos nombres/alias en el CSV. Esta funcion busca primero por
CUIT (mas confiable), despues por alias exacto de nombre, y si no encuentra nada
propone crear un proveedor nuevo (con su alias) sin bloquear la importacion --
la creacion automatica queda registrada para que el validador la revise.
"""
from sqlalchemy.orm import Session

from app.models.catalog import Provider, ProviderAlias


def normalize_cuit(cuit_raw) -> str | None:
    if cuit_raw is None:
        return None
    digits = "".join(ch for ch in str(cuit_raw) if ch.isdigit())
    return digits or None


def find_or_propose_provider(db: Session, cuit_raw, razon_social: str | None) -> tuple[Provider | None, bool]:
    """
    Devuelve (provider, fue_creado_automaticamente).
    Si no hay coincidencia por CUIT ni por alias de nombre, crea un proveedor nuevo
    'tal cual' (nombre_normalizado = razon_social) con su alias, para no bloquear
    la carga -- el Administrador lo puede renombrar/fusionar despues (sección 8.1).
    """
    cuit = normalize_cuit(cuit_raw)

    if cuit:
        provider = db.query(Provider).filter(Provider.cuit == cuit).first()
        if provider:
            return provider, False

    if razon_social:
        alias = (
            db.query(ProviderAlias)
            .filter(ProviderAlias.alias_texto == razon_social.strip())
            .first()
        )
        if alias:
            return alias.provider, False

    if not razon_social:
        return None, False

    nombre = razon_social.strip()
    provider = Provider(nombre_normalizado=nombre, cuit=cuit)
    db.add(provider)
    db.flush()
    db.add(ProviderAlias(provider_id=provider.id, alias_texto=nombre))
    return provider, True
