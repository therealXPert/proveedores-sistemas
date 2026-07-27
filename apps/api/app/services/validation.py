"""
Validaciones de datos (sección 6) y deteccion de duplicados (sección 19) del diseño.
Cada validacion devuelve una lista de (tipo, severidad, mensaje); severidad es
'bloqueante' | 'advertencia' | 'info'. Una fila con al menos un error 'bloqueante'
no puede aprobarse hasta corregirse o excluirse.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.invoicing import Invoice

MONEDAS_VALIDAS = {"ARS", "Pesos", "USD", "Dolares", "Dólares"}

# Tipo de Documento reales observados (sección 19): las notas no se bloquean como duplicado de su factura origen
TIPOS_NOTA = {"Nota de Credito", "Nota Credito", "Nota de Debito", "Nota Debito"}


def validar_fila(mapped: dict, provider_encontrado: bool) -> list[tuple[str, str, str]]:
    errores = []

    if not mapped.get("fecha_emision"):
        errores.append(("fecha_invalida", "bloqueante", "Fecha de factura vacia o con formato no reconocido"))

    importe = mapped.get("importe_total")
    if importe is None:
        errores.append(("importe_invalido", "bloqueante", "Importe Total vacio o con formato no reconocido"))
    elif isinstance(importe, Decimal) and importe < 0:
        tipo_doc = (mapped.get("tipo_documento") or "").strip()
        if tipo_doc not in TIPOS_NOTA:
            errores.append(("importe_negativo_inesperado", "advertencia", f"Importe negativo en un documento de tipo '{tipo_doc}'"))

    moneda = (mapped.get("moneda") or "").strip()
    if moneda and moneda not in MONEDAS_VALIDAS:
        errores.append(("moneda_desconocida", "advertencia", f"Moneda no reconocida: '{moneda}'"))

    if not provider_encontrado:
        errores.append(("proveedor_creado_automaticamente", "advertencia", "Proveedor no existia; se creo automaticamente, revisar antes de aprobar"))

    if not mapped.get("numero_factura"):
        errores.append(("numero_factura_vacio", "advertencia", "Numero de Factura vacio"))

    return errores


def detectar_duplicado_contra_aprobadas(db: Session, provider_id: int | None, mapped: dict) -> Invoice | None:
    """
    Combinacion de deteccion (sección 19): proveedor + numero de factura + importe + moneda.
    No se aplica a Notas de Credito/Debito (nunca se bloquean como duplicado de su factura origen).
    """
    tipo_doc = (mapped.get("tipo_documento") or "").strip()
    if tipo_doc in TIPOS_NOTA:
        return None

    if not provider_id or not mapped.get("numero_factura"):
        return None

    query = db.query(Invoice).filter(
        Invoice.provider_id == provider_id,
        Invoice.numero_factura == mapped.get("numero_factura"),
        Invoice.estado == "aprobado",
    )
    importe = mapped.get("importe_total")
    if importe is not None:
        query = query.filter(Invoice.importe_total == importe)

    return query.first()


def detectar_duplicado_en_mismo_archivo(filas_previas: list[dict], mapped: dict) -> bool:
    """Duplicado dentro del mismo archivo (misma corrida de importacion), comparando proveedor+numero+importe."""
    tipo_doc = (mapped.get("tipo_documento") or "").strip()
    if tipo_doc in TIPOS_NOTA:
        return False

    clave = (mapped.get("cuit"), mapped.get("numero_factura"), mapped.get("importe_total"))
    if not all(clave):
        return False

    for previa in filas_previas:
        clave_previa = (previa.get("cuit"), previa.get("numero_factura"), previa.get("importe_total"))
        if clave_previa == clave:
            return True
    return False
