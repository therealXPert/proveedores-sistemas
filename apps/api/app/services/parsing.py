"""
Parseo de fechas e importes tolerante a los formatos reales encontrados:
- Fechas: vienen como datetime nativo cuando el archivo es .xlsx (pandas/openpyxl
  ya las interpreta), o como texto dd/mm/aaaa en CSV exportados.
- Importes: en CSV llegan como texto con coma decimal (ej. '46786.66' o '38.666,66'
  segun el archivo); en xlsx llegan ya como float. Se soportan ambos separadores.
"""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation


def parse_fecha(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    texto = str(value).strip()
    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


def parse_importe(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    texto = str(value).strip().replace("$", "").replace(" ", "")
    if not texto:
        return None

    # Si tiene coma Y punto: el ultimo separador es el decimal (formato AR: 1.234,56)
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        # Solo coma: se asume que es el separador decimal (formato AR sin miles)
        texto = texto.replace(",", ".")

    try:
        return Decimal(texto)
    except InvalidOperation:
        return None
