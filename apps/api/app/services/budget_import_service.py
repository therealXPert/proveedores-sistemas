"""
Importa Presupuesto_Sistemas.xlsx (semilla real del módulo de presupuesto,
ver addendum #28 del documento de diseño). Normaliza:
- Área: el archivo trae valores abreviados ("APN", "Tecnología", "Mesa de
  Servicio") que hay que mapear a los nombres completos usados en el resto
  del sistema. Los casos multi-área ("Mesa de Servicio, Tecnologia") NO se
  reparten aca -- se resuelven por factura durante la validación (decisión
  ya tomada), y quedan solo como nota en el comentario.
- Periodicidad -> importe mensual equivalente: Mensual tal cual, Bimensual/2,
  Trimestral/3, "A demanda" sin equivalente mensual fijo (queda None).
"""
import io
from decimal import Decimal

import openpyxl
from sqlalchemy.orm import Session

from app.models.catalog import Area, BusinessUnit
from app.models.budget import Budget, BudgetVersion
from app.services.provider_matching import find_or_propose_provider

AREA_MAP = {
    "apn": "Sistemas Aplicaciones Negocio",
    "tecnologia": "Sistemas Tecnologia y Operaciones",
    "tecnología": "Sistemas Tecnologia y Operaciones",
    "mesa de servicio": "Sistemas Mesa de Servicio",
}


def _normalize_area(raw):
    """Devuelve (nombre_area_completo_o_None, texto_original_si_es_multivalor_o_None)."""
    if not raw:
        return None, None
    texto = str(raw).strip()
    if "," in texto:
        return None, texto
    return AREA_MAP.get(texto.lower()), None


def _periodicidad_a_mensual(importe: Decimal | None, periodicidad) -> Decimal | None:
    if importe is None:
        return None
    p = str(periodicidad or "").strip().lower()
    if p == "mensual":
        return importe
    if p == "bimensual":
        return importe / 2
    if p == "trimestral":
        return importe / 3
    return None  # "a demanda" u otra: sin equivalente mensual fijo


def import_presupuesto_sistemas(
    db: Session, content: bytes, budget_version: BudgetVersion, anio: int = 2026
) -> dict:
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb["Hoja 1"]

    creados = 0
    proveedores_creados = 0
    sin_importe = 0
    filas_multi_area = 0

    for row in ws.iter_rows(min_row=3, values_only=True):
        if len(row) < 10:
            continue
        _, razon_social, nombre, cuit_raw, area_raw, detalle, unidad_negocio_raw, periodicidad, importe, observacion = row[:10]

        nombre_proveedor = razon_social or nombre
        if not nombre_proveedor:
            continue

        provider, creado_auto = find_or_propose_provider(db, cuit_raw, nombre_proveedor)
        if creado_auto:
            proveedores_creados += 1

        area_nombre, area_raw_multi = _normalize_area(area_raw)
        area = db.query(Area).filter(Area.nombre_normalizado == area_nombre).first() if area_nombre else None
        if area_raw_multi:
            filas_multi_area += 1

        business_unit = None
        if unidad_negocio_raw:
            business_unit = db.query(BusinessUnit).filter(BusinessUnit.nombre == str(unidad_negocio_raw).strip()).first()

        importe_decimal = Decimal(str(importe)) if importe is not None else None
        if importe_decimal is None:
            sin_importe += 1

        mensual = _periodicidad_a_mensual(importe_decimal, periodicidad)

        partes_comentario = []
        if detalle:
            partes_comentario.append(f"Detalle: {detalle}")
        if observacion:
            partes_comentario.append(f"Observación: {observacion}")
        if area_raw_multi:
            partes_comentario.append(f"Área original (multivalor, no repartida): {area_raw_multi}")
        comentario = " | ".join(partes_comentario) or None

        db.add(Budget(
            budget_version_id=budget_version.id,
            anio=anio,
            mes=None,
            provider_id=provider.id if provider else None,
            area_id=area.id if area else None,
            business_unit_id=business_unit.id if business_unit else None,
            moneda="ARS",
            periodicidad_original=str(periodicidad) if periodicidad else None,
            importe_original=importe_decimal,
            importe_mensual_equivalente=mensual,
            comentario=comentario,
        ))
        creados += 1

    db.commit()
    return {
        "presupuestos_creados": creados,
        "proveedores_creados_automaticamente": proveedores_creados,
        "filas_sin_importe": sin_importe,
        "filas_multi_area": filas_multi_area,
    }
