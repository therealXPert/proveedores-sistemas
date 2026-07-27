"""
Mapeo configurable de columnas del CSV/XLSX de TSDocs a campos internos (sección 7
del diseño). No asume que el nombre de columna sea siempre idéntico: en los archivos
reales analizados aparecieron variantes por tildes ('Área'/'Area') y por problemas
de codificación ('A\x81rea'). Por eso el mapeo normaliza el encabezado (sin tildes,
sin caracteres de control, en minúsculas) antes de buscar la coincidencia exacta.

Este mapeo default representa la plantilla base de TSDocs (import_templates /
import_template_versions en la base). Mas adelante se puede permitir crear otras
plantillas desde la UI; por ahora esta funcion cubre el 100% de las columnas reales
vistas en Tec-2026.xlsx, APN-2026.xlsx, Mesa-2026.xlsx y los 3 CSV originales.
"""
import re
import unicodedata


# clave normalizada -> campo interno (None = se guarda en crudo pero no se mapea a un campo propio)
CANONICAL_MAP = {
    "id documento": "identificador_externo_tsdocs",
    "empresa": "empresa_nombre",
    "sucursal": "sucursal_nombre",
    "area": "area_nombre",
    "numero de factura": "numero_factura",
    "letra arca": "letra_arca",
    "cuit": "cuit",
    "razon social": "proveedor_razon_social",
    "razon social que factura": "proveedor_razon_social",
    "tipo de documento": "tipo_documento",
    "fecha de factura": "fecha_emision",
    "importe total": "importe_total",
    "moneda": "moneda",
    "tasa": "tasa_cambio",
    "importe en dolares": "importe_en_dolares",
    "estado facturas": "estado_facturas_origen",
    "cae": "cae",
    "orden de compra": "orden_compra",
    "nombre o email del colaborador autocity o g tagle que solicita": "solicitante",
    "descripcion": "descripcion",
    "forma de pago": "forma_pago",
    "cuenta personal": "cuenta_personal",
    "vencimiento": "condicion_pago",
    "fecha vencimiento": "fecha_vencimiento",
    "importe sin impuestos": "importe_neto",
    "observaciones": "observaciones",
    "link documento": "link_documento_original",
}

def normalize_header(header: str) -> str:
    if header is None:
        return ""
    # Elimina caracteres de control (ej. el 'A\x81rea' visto en Mesa-2026.xlsx)
    header = "".join(ch for ch in header if unicodedata.category(ch)[0] != "C")
    header = unicodedata.normalize("NFKD", header)
    header = "".join(ch for ch in header if not unicodedata.combining(ch))
    header = header.lower().strip()
    header = re.sub(r"[^a-z0-9]+", " ", header)
    header = re.sub(r"\s+", " ", header).strip()
    return header


def build_column_mapping(headers: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    Devuelve (mapeo, columnas_desconocidas):
    - mapeo: {encabezado_original: campo_interno}
    - columnas_desconocidas: encabezados que no se pudieron mapear (sección 6: 'Columnas desconocidas')

    Solo hace matching EXACTO despues de normalizar (sin tildes, sin caracteres de
    control, en minusculas). Se probo con fuzzy matching (coincidencia difusa) pero
    generaba falsos positivos entre columnas parecidas pero distintas (ej. la columna
    de texto 'Vencimiento CAE' terminaba mapeada como si fuera 'Vencimiento'/plazo de
    pago). Con normalizacion exacta ya se resuelven los casos reales encontrados
    (tildes: 'Área'/'Area', bytes corruptos: 'A\\x81rea'). Cualquier columna nueva que
    TSDocs agregue en el futuro debe sumarse explicitamente a CANONICAL_MAP.
    """
    mapping: dict[str, str] = {}
    unknown: list[str] = []

    for original in headers:
        normalized = normalize_header(original)
        if normalized in CANONICAL_MAP:
            mapping[original] = CANONICAL_MAP[normalized]
        else:
            unknown.append(original)

    return mapping, unknown


def apply_mapping(raw_row: dict, mapping: dict[str, str]) -> dict:
    """Traduce una fila cruda ({encabezado_original: valor}) a campos internos."""
    mapped = {}
    for original_header, value in raw_row.items():
        campo = mapping.get(original_header)
        if campo:
            mapped[campo] = value
    return mapped
