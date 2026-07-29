"""
Tests de integracion del importador, usando un CSV con la estructura real de
TSDocs (tests/fixtures/tsdocs_sample.csv). Cubre: mapeo de columnas, parseo de
fechas/importes, normalizacion de proveedor/area/categoria, deteccion de
duplicados (en el mismo archivo), advertencias (moneda desconocida, importe
negativo inesperado), y el flujo de aprobacion.
"""
from pathlib import Path

from app.services.import_service import process_uploaded_file
from app.services.approval_service import approve_pending_in_batch
from app.models.invoicing import Invoice
from app.models.catalog import Provider, Area

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "tsdocs_sample.csv"


def _load_fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_process_uploaded_file_creates_batch_with_expected_summary(db_session, admin_user, seeded_catalogs):
    content = _load_fixture_bytes()
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", content)

    assert batch.id is not None
    # 5 filas en el fixture: 2 limpias, 1 con moneda desconocida (advertencia),
    # 1 con importe negativo inesperado (advertencia), 1 duplicada de la fila 2 (advertencia)
    assert batch.resumen_json["total_filas"] == 5
    assert batch.resumen_json["invalidos"] == 0
    assert batch.resumen_json["advertencias"] >= 3
    assert batch.estado == "pendiente_validacion"


def test_moneda_desconocida_genera_advertencia(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    tipos_error = [e.tipo for s in batch.staging_invoices for e in s.errores]
    assert "moneda_desconocida" in tipos_error


def test_importe_negativo_inesperado_genera_advertencia(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    tipos_error = [e.tipo for s in batch.staging_invoices for e in s.errores]
    assert "importe_negativo_inesperado" in tipos_error


def test_duplicado_en_archivo_detectado(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    tipos_error = [e.tipo for s in batch.staging_invoices for e in s.errores]
    assert "duplicado_en_archivo" in tipos_error


def test_proveedores_normalizados_se_crean(db_session, admin_user, seeded_catalogs):
    process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    nombres = {p.nombre_normalizado for p in db_session.query(Provider).all()}
    assert "STEFANO LORENZO" in nombres
    assert "ULTRAIT S.A." in nombres


def test_areas_normalizadas_se_crean(db_session, admin_user, seeded_catalogs):
    process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    nombres = {a.nombre_normalizado for a in db_session.query(Area).all()}
    assert "Sistemas Aplicaciones Negocio" in nombres
    assert "Sistemas Mesa de Servicio" in nombres


def test_approve_batch_crea_invoices_para_filas_no_bloqueantes(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    resultado = approve_pending_in_batch(db_session, batch, admin_user.id)

    # Ninguna fila del fixture es bloqueante (todo lo malo es 'advertencia'), asi que las 5 se aprueban
    assert resultado["filas_aprobadas"] == 5
    assert resultado["filas_excluidas_por_error"] == 0
    assert db_session.query(Invoice).count() == 5
    assert batch.estado == "aprobado"


def test_segunda_importacion_detecta_duplicado_contra_aprobadas(db_session, admin_user, seeded_catalogs):
    batch1 = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    approve_pending_in_batch(db_session, batch1, admin_user.id)

    # Se vuelve a subir el mismo archivo: ahora TODAS las filas deberian marcarse como duplicado
    # contra facturas ya aprobadas (bloqueante), salvo que la logica de deteccion falle.
    batch2 = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    tipos_error = [e.tipo for s in batch2.staging_invoices for e in s.errores]
    assert "duplicado_factura_existente" in tipos_error
    assert batch2.estado == "con_errores"


def test_approve_batch_con_muchas_filas_no_falla(db_session, admin_user, seeded_catalogs):
    """
    Regresion: aprobar un batch con muchas filas activaba una optimizacion de
    SQLAlchemy (insertmanyvalues) que en la practica generaba un INSERT masivo
    con datos desalineados contra PostgreSQL. Se soluciono haciendo flush() por
    cada factura en approval_service.py. Este test simula un batch grande
    (100 filas) para evitar que la regresion vuelva a pasar inadvertida.
    """
    import csv
    import io

    from app.services.import_service import process_uploaded_file

    header = "Id Documento;Empresa;Sucursal;Área;Número de Factura;CUIT;Razón Social que Factura;Tipo de Documento;Fecha de Factura;Importe Total;Moneda;Descripción;Cuenta Personal"
    filas = [header]
    for i in range(100):
        filas.append(
            f"{200000+i};TAGLE;Cordoba;Sistemas Aplicaciones Negocio;00001-{i:08d};30709988464;"
            f"PROVEEDOR TEST {i};Factura;02/01/2026;{1000 + i}.50;Pesos;Descripcion de prueba {i};"
            "SISTEMAS - LICENCIAS SISTEMAS - ST07"
        )
    contenido = ("\n".join(filas)).encode("utf-8")

    batch = process_uploaded_file(db_session, admin_user.id, "prueba_100_filas.csv", contenido)
    assert batch.resumen_json["total_filas"] == 100

    from app.services.approval_service import approve_pending_in_batch
    resultado = approve_pending_in_batch(db_session, batch, admin_user.id)
    assert resultado["filas_aprobadas"] == 100

    from app.models.invoicing import Invoice
    assert db_session.query(Invoice).count() == 100


def test_approve_una_sola_fila_no_afecta_al_resto(db_session, admin_user, seeded_catalogs):
    """El punto central del pedido: aprobar/rechazar factura por factura, no solo el lote entero."""
    from app.services.approval_service import approve_staging_row, reject_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    filas = batch.staging_invoices

    # Aprobamos la primera fila nomas
    invoice = approve_staging_row(db_session, filas[0], admin_user.id)
    assert invoice.id is not None
    assert filas[0].resultado == "aprobada"
    assert filas[0].invoice_id == invoice.id

    # El resto sigue pendiente, el batch todavia no esta cerrado
    assert all(f.resultado == "pendiente" for f in filas[1:])
    assert batch.estado in ("pendiente_validacion", "con_errores")

    # Rechazamos la segunda
    reject_staging_row(db_session, filas[1], admin_user.id, "duplicada con otra carga")
    assert filas[1].resultado == "rechazada"
    assert filas[1].motivo_rechazo == "duplicada con otra carga"

    assert db_session.query(Invoice).count() == 1


def test_no_se_puede_procesar_una_fila_dos_veces(db_session, admin_user, seeded_catalogs):
    from app.services.approval_service import approve_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    fila = batch.staging_invoices[0]

    approve_staging_row(db_session, fila, admin_user.id)
    with __import__("pytest").raises(ValueError):
        approve_staging_row(db_session, fila, admin_user.id)


def test_batch_pasa_a_aprobado_cuando_no_quedan_filas_pendientes(db_session, admin_user, seeded_catalogs):
    from app.services.approval_service import approve_staging_row, reject_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    filas = batch.staging_invoices

    for i, fila in enumerate(filas):
        if i == 0:
            reject_staging_row(db_session, fila, admin_user.id, "no corresponde")
        else:
            approve_staging_row(db_session, fila, admin_user.id)

    assert batch.estado == "aprobado"
    assert db_session.query(Invoice).count() == len(filas) - 1


def test_batch_queda_rechazado_si_se_rechazan_todas_las_filas(db_session, admin_user, seeded_catalogs):
    from app.services.approval_service import reject_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    for fila in batch.staging_invoices:
        reject_staging_row(db_session, fila, admin_user.id, "archivo incorrecto")

    assert batch.estado == "rechazado"
    assert db_session.query(Invoice).count() == 0


def test_approve_pending_in_batch_respeta_decisiones_previas(db_session, admin_user, seeded_catalogs):
    """El atajo de lote no debe re-procesar filas que un usuario ya decidio individualmente."""
    from app.services.approval_service import reject_staging_row, approve_pending_in_batch

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    filas = batch.staging_invoices

    reject_staging_row(db_session, filas[0], admin_user.id, "no corresponde")

    resultado = approve_pending_in_batch(db_session, batch, admin_user.id)

    assert filas[0].resultado == "rechazada"  # no se toco
    assert resultado["filas_aprobadas"] == len(filas) - 1
    assert db_session.query(Invoice).count() == len(filas) - 1
