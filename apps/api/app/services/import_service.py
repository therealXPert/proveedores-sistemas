"""
Orquesta el flujo completo de importacion (sección 5 del diseño):
archivo -> deteccion de estructura -> mapeo -> staging con validaciones -> resumen.
La aprobacion (staging -> invoices definitivas) esta en approve_batch().
"""
import hashlib

import pandas as pd
from sqlalchemy.orm import Session

from app.models.importing import ImportFile, ImportBatch, StagingInvoice, ValidationError
from app.models.invoicing import Invoice
from app.services import storage_service, catalog_matching, provider_matching, validation
from app.services.file_detection import detect_structure, read_rows_as_dicts
from app.services.json_utils import to_json_safe
from app.services.mapping import build_column_mapping, apply_mapping
from app.services.parsing import parse_fecha, parse_importe


def _clean_nan(value):
    """Pandas representa celdas vacias de xlsx como NaN/NaT, no como None."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def process_uploaded_file(db: Session, user_id: int, filename: str, content: bytes) -> ImportBatch:
    file_hash = hashlib.sha256(content).hexdigest()
    gcs_path = storage_service.save_file(filename, content)

    import_file = ImportFile(
        nombre_original=filename,
        gcs_path=gcs_path,
        hash_archivo=file_hash,
        subido_por_id=user_id,
    )
    db.add(import_file)
    db.flush()

    structure = detect_structure(filename, content)
    mapping, columnas_desconocidas = build_column_mapping(structure.encabezados)
    raw_rows = read_rows_as_dicts(filename, content, structure)

    batch = ImportBatch(
        import_file_id=import_file.id,
        template_version_id=None,  # el MVP usa el mapeo default (ver app/services/mapping.py); ver nota en README
        estado="procesando",
    )
    db.add(batch)
    db.flush()

    contadores = {"validos": 0, "advertencias": 0, "invalidos": 0, "duplicados": 0}
    filas_procesadas: list[dict] = []
    tiene_bloqueante = False

    for raw_row in raw_rows:
        mapped_raw = apply_mapping(raw_row, mapping)
        mapped_raw = {k: _clean_nan(v) for k, v in mapped_raw.items()}

        mapped = dict(mapped_raw)
        mapped["fecha_emision"] = parse_fecha(mapped_raw.get("fecha_emision"))
        mapped["fecha_vencimiento"] = parse_fecha(mapped_raw.get("fecha_vencimiento"))
        mapped["importe_total"] = parse_importe(mapped_raw.get("importe_total"))
        mapped["importe_neto"] = parse_importe(mapped_raw.get("importe_neto"))
        mapped["importe_en_dolares"] = parse_importe(mapped_raw.get("importe_en_dolares"))
        mapped["tasa_cambio"] = parse_importe(mapped_raw.get("tasa_cambio"))

        provider, creado_auto = provider_matching.find_or_propose_provider(
            db, mapped_raw.get("cuit"), mapped_raw.get("proveedor_razon_social")
        )
        area = catalog_matching.get_or_create_area(db, mapped_raw.get("area_nombre"))
        company = catalog_matching.get_or_create_company(db, mapped_raw.get("empresa_nombre"))
        branch = catalog_matching.get_or_create_branch(db, mapped_raw.get("sucursal_nombre"))
        category, cost_center, advertencia_cuenta = catalog_matching.get_category_and_cost_center(
            db, mapped_raw.get("cuenta_personal")
        )

        mapped["provider_id"] = provider.id if provider else None
        mapped["area_id"] = area.id if area else None
        mapped["company_id"] = company.id if company else None
        mapped["branch_id"] = branch.id if branch else None
        mapped["category_id"] = category.id if category else None
        mapped["cost_center_id"] = cost_center.id if cost_center else None

        errores = validation.validar_fila(mapped, provider_encontrado=(provider is not None and not creado_auto))
        if advertencia_cuenta:
            errores.append(("cuenta_personal_no_reconocida", "advertencia", advertencia_cuenta))

        duplicado_invoice = validation.detectar_duplicado_contra_aprobadas(db, mapped.get("provider_id"), mapped)
        es_duplicado_en_archivo = validation.detectar_duplicado_en_mismo_archivo(filas_procesadas, mapped_raw)

        if duplicado_invoice:
            errores.append(("duplicado_factura_existente", "bloqueante", f"Ya existe la factura aprobada #{duplicado_invoice.id} con el mismo proveedor/numero/importe"))
        if es_duplicado_en_archivo:
            errores.append(("duplicado_en_archivo", "advertencia", "Fila repetida dentro del mismo archivo (mismo CUIT/numero/importe)"))

        severidades = {sev for _, sev, _ in errores}
        if "bloqueante" in severidades:
            estado_fila = "error"
            contadores["invalidos"] += 1
            tiene_bloqueante = True
        elif "advertencia" in severidades:
            estado_fila = "advertencia"
            contadores["advertencias"] += 1
        else:
            estado_fila = "valida"
            contadores["validos"] += 1

        if duplicado_invoice or es_duplicado_en_archivo:
            contadores["duplicados"] += 1

        staging = StagingInvoice(
            import_batch_id=batch.id,
            datos_crudos_json=to_json_safe(raw_row),
            datos_mapeados_json=to_json_safe(mapped),
            estado_fila=estado_fila,
            es_duplicado_de_invoice_id=duplicado_invoice.id if duplicado_invoice else None,
        )
        db.add(staging)
        db.flush()

        for tipo, severidad, mensaje in errores:
            db.add(ValidationError(staging_invoice_id=staging.id, tipo=tipo, severidad=severidad, mensaje=mensaje))

        filas_procesadas.append(mapped_raw)

    batch.estado = "con_errores" if tiene_bloqueante else "pendiente_validacion"
    batch.resumen_json = {
        **contadores,
        "total_filas": len(raw_rows),
        "columnas_desconocidas": columnas_desconocidas,
        "encoding_detectado": structure.encoding,
        "separador_detectado": structure.separador,
    }
    db.commit()
    return batch
