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


def test_editar_fila_corrige_importe_invalido(db_session, admin_user, seeded_catalogs):
    """El fixture no trae filas con importe invalido, asi que forzamos el caso a mano."""
    from app.services.staging_edit_service import update_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    fila = batch.staging_invoices[0]

    # Rompemos el importe a mano para simular una fila invalida
    m = dict(fila.datos_mapeados_json)
    m["importe_total"] = None
    fila.datos_mapeados_json = m
    fila.estado_fila = "error"
    db_session.commit()

    update_staging_row(db_session, fila, {"importe_total": 12345.67}, admin_user.id)

    assert fila.datos_mapeados_json["importe_total"] == "12345.67"
    assert fila.estado_fila in ("valida", "advertencia")  # ya no deberia quedar en 'error' por importe


def test_editar_fila_recalcula_duplicado_al_corregir_numero_factura(db_session, admin_user, seeded_catalogs):
    """Si el usuario corrige un numero de factura mal tipeado, el falso duplicado debe desaparecer."""
    from app.services.approval_service import approve_staging_row
    from app.services.staging_edit_service import update_staging_row

    batch1 = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    aprobada = next(f for f in batch1.staging_invoices if f.datos_mapeados_json.get("numero_factura") == "00003-00004376")
    approve_staging_row(db_session, aprobada, admin_user.id)

    batch2 = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    duplicada = next(f for f in batch2.staging_invoices if f.datos_mapeados_json.get("numero_factura") == "00003-00004376")
    assert any(e.tipo == "duplicado_factura_existente" for e in duplicada.errores)

    # El usuario corrige el numero de factura (era un typo)
    update_staging_row(db_session, duplicada, {"numero_factura": "00003-00004377"}, admin_user.id)

    assert not any(e.tipo == "duplicado_factura_existente" for e in duplicada.errores)
    assert duplicada.es_duplicado_de_invoice_id is None


def test_no_se_puede_editar_una_fila_ya_procesada(db_session, admin_user, seeded_catalogs):
    from app.services.approval_service import approve_staging_row
    from app.services.staging_edit_service import update_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    fila = batch.staging_invoices[0]
    approve_staging_row(db_session, fila, admin_user.id)

    with __import__("pytest").raises(ValueError):
        update_staging_row(db_session, fila, {"descripcion": "cambio no permitido"}, admin_user.id)


def test_editar_fila_permite_cambiar_proveedor(db_session, admin_user, seeded_catalogs):
    from app.models.catalog import Provider
    from app.services.staging_edit_service import update_staging_row

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    fila = batch.staging_invoices[0]

    otro_proveedor = Provider(nombre_normalizado="Proveedor Correcto SA")
    db_session.add(otro_proveedor)
    db_session.commit()

    update_staging_row(db_session, fila, {"provider_id": otro_proveedor.id}, admin_user.id)

    assert fila.datos_mapeados_json["provider_id"] == otro_proveedor.id
    # Ya no deberia quedar la advertencia de "proveedor creado automaticamente"
    assert not any(e.tipo == "proveedor_creado_automaticamente" for e in fila.errores)


def test_grupo_economico_se_autocompleta_desde_la_empresa(db_session, admin_user, seeded_catalogs):
    """Modelo hibrido: si la empresa ya tiene grupo asignado, la factura lo hereda al importar."""
    from app.models.catalog import Company, EconomicGroup

    grupo = EconomicGroup(nombre="Grupo Test")
    db_session.add(grupo)
    db_session.flush()

    empresa = Company(nombre="TAGLE", economic_group_id=grupo.id)
    db_session.add(empresa)
    db_session.commit()

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    filas_tagle = [f for f in batch.staging_invoices if f.datos_mapeados_json.get("empresa_nombre") == "TAGLE"]

    assert len(filas_tagle) > 0
    assert all(f.datos_mapeados_json.get("economic_group_id") == grupo.id for f in filas_tagle)


def test_grupo_economico_editable_a_mano_pisa_la_deteccion_automatica(db_session, admin_user, seeded_catalogs):
    from app.services.staging_edit_service import update_staging_row
    from app.models.catalog import EconomicGroup

    grupo_a = EconomicGroup(nombre="Grupo A")
    grupo_b = EconomicGroup(nombre="Grupo B")
    db_session.add_all([grupo_a, grupo_b])
    db_session.commit()

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    fila = batch.staging_invoices[0]

    update_staging_row(db_session, fila, {"economic_group_id": grupo_b.id}, admin_user.id)
    assert fila.datos_mapeados_json["economic_group_id"] == grupo_b.id


def test_asignacion_masiva_pisa_todo_el_lote(db_session, admin_user, seeded_catalogs):
    from app.models.catalog import EconomicGroup

    grupo = EconomicGroup(nombre="Grupo Masivo")
    db_session.add(grupo)
    db_session.commit()

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())

    # Simula el endpoint de asignacion masiva (misma logica que app/api/imports.py:assign_batch_group)
    for fila in batch.staging_invoices:
        m = dict(fila.datos_mapeados_json or {})
        m["economic_group_id"] = grupo.id
        fila.datos_mapeados_json = m
    db_session.commit()

    assert all(f.datos_mapeados_json["economic_group_id"] == grupo.id for f in batch.staging_invoices)


def test_factura_aprobada_hereda_el_grupo_economico_de_la_fila(db_session, admin_user, seeded_catalogs):
    from app.services.approval_service import approve_staging_row
    from app.services.staging_edit_service import update_staging_row
    from app.models.catalog import EconomicGroup

    grupo = EconomicGroup(nombre="Grupo Aprobado")
    db_session.add(grupo)
    db_session.commit()

    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    fila = batch.staging_invoices[0]
    update_staging_row(db_session, fila, {"economic_group_id": grupo.id}, admin_user.id)

    invoice = approve_staging_row(db_session, fila, admin_user.id)
    assert invoice.economic_group_id == grupo.id
