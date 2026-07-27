"""
Sanitizacion recursiva de valores antes de guardarlos en una columna JSON.
Necesario porque pandas devuelve tipos que el encoder JSON estandar no entiende
(Timestamp, numpy.int64/float64, NaN) tanto en filas de .xlsx como, a veces, en
columnas numericas de .csv leidas con pandas.
"""
from datetime import datetime, date
from decimal import Decimal

import pandas as pd


def to_json_safe(value):
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(v) for v in value]

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "isoformat"):  # pandas.Timestamp y similares
        return value.isoformat()

    # numpy.int64/float64/bool_: convertir a tipos nativos de Python
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value
