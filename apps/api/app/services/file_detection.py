"""
Deteccion automatica de la estructura de un archivo subido (sección 5 del diseño):
separador, codificacion, encabezados, formato de fechas, formato de numeros.

Soporta .csv (con deteccion de separador/encoding) y .xlsx (via pandas/openpyxl,
que no necesitan deteccion de separador/encoding porque son binarios estructurados).
"""
import csv
import io
from dataclasses import dataclass, field
from typing import Optional

import chardet
import pandas as pd


@dataclass
class FileStructure:
    tipo_archivo: str  # "csv" o "xlsx"
    encoding: Optional[str] = None
    separador: Optional[str] = None
    encabezados: list[str] = field(default_factory=list)
    cantidad_filas: int = 0
    hoja: Optional[str] = None  # solo para xlsx


def detect_csv_structure(raw_bytes: bytes) -> FileStructure:
    encoding_guess = chardet.detect(raw_bytes)
    encoding = encoding_guess.get("encoding") or "utf-8"

    try:
        text_sample = raw_bytes[:8192].decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        encoding = "utf-8"
        text_sample = raw_bytes[:8192].decode(encoding, errors="replace")

    try:
        dialect = csv.Sniffer().sniff(text_sample, delimiters=";,|\t")
        separador = dialect.delimiter
    except csv.Error:
        # Fallback: TSDocs exporta con ';' en la mayoria de los casos observados
        separador = ";"

    full_text = raw_bytes.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(full_text), delimiter=separador)
    rows = list(reader)
    encabezados = rows[0] if rows else []

    return FileStructure(
        tipo_archivo="csv",
        encoding=encoding,
        separador=separador,
        encabezados=encabezados,
        cantidad_filas=max(len(rows) - 1, 0),
    )


def detect_xlsx_structure(raw_bytes: bytes) -> FileStructure:
    excel_file = pd.ExcelFile(io.BytesIO(raw_bytes))
    hoja = excel_file.sheet_names[0]
    df = excel_file.parse(hoja, nrows=0)  # solo encabezados, rapido incluso en archivos grandes
    df_full = excel_file.parse(hoja)

    return FileStructure(
        tipo_archivo="xlsx",
        encabezados=list(df.columns),
        cantidad_filas=len(df_full),
        hoja=hoja,
    )


def detect_structure(filename: str, raw_bytes: bytes) -> FileStructure:
    if filename.lower().endswith((".xlsx", ".xls")):
        return detect_xlsx_structure(raw_bytes)
    return detect_csv_structure(raw_bytes)


def read_rows_as_dicts(filename: str, raw_bytes: bytes, structure: FileStructure) -> list[dict]:
    """Devuelve cada fila del archivo como un diccionario {encabezado: valor}, en el orden original."""
    if structure.tipo_archivo == "xlsx":
        df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=structure.hoja)
        df = df.where(pd.notnull(df), None)
        return df.to_dict(orient="records")

    text = raw_bytes.decode(structure.encoding or "utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=structure.separador or ";")
    return list(reader)
