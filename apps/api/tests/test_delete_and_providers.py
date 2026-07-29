"""Tests de: borrado fisico de importaciones (con sus casos limite de FK) y fusion de proveedores."""
from pathlib import Path

from app.services.import_service import process_uploaded_file
from app.services.approval_service import approve_pending_in_batch
from app.services.import_delete_service import delete_import_batch
from app.services.provider_service import merge_providers
from app.models.invoicing import Invoice
from app.models.importing import ImportBatch
from app.models.catalog import Provider, ProviderAlias
from app.models.audit import AuditEvent

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "tsdocs_sample.csv"


def _load_fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_eliminar_batch_no_aprobado(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    resultado = delete_import_batch(db_session, batch, admin_user.id)

    assert resultado["facturas_eliminadas"] == 0
    assert db_session.query(ImportBatch).count() == 0


def test_eliminar_batch_aprobado_borra_sus_facturas(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    approve_pending_in_batch(db_session, batch, admin_user.id)
    assert db_session.query(Invoice).count() > 0

    resultado = delete_import_batch(db_session, batch, admin_user.id)

    assert resultado["facturas_eliminadas"] > 0
    assert db_session.query(Invoice).count() == 0
    assert db_session.query(ImportBatch).count() == 0


def test_eliminar_batch_referenciado_por_otro_no_rompe_fk(db_session, admin_user, seeded_catalogs):
    """Caso limite real: otro batch tiene filas marcadas como duplicado de facturas de este batch."""
    batch1 = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    approve_pending_in_batch(db_session, batch1, admin_user.id)

    batch2 = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    tipos_antes = [e.tipo for s in batch2.staging_invoices for e in s.errores]
    assert "duplicado_factura_existente" in tipos_antes

    # No debe lanzar ninguna excepcion de integridad referencial
    delete_import_batch(db_session, batch1, admin_user.id)

    db_session.refresh(batch2)
    tipos_despues = [e.tipo for s in batch2.staging_invoices for e in s.errores]
    assert "duplicado_factura_existente" not in tipos_despues
    assert all(s.estado_fila != "error" or "duplicado_factura_existente" not in [e.tipo for e in s.errores] for s in batch2.staging_invoices)


def test_eliminar_batch_preserva_auditoria(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    approve_pending_in_batch(db_session, batch, admin_user.id)

    eventos_antes = db_session.query(AuditEvent).count()
    delete_import_batch(db_session, batch, admin_user.id)
    eventos_despues = db_session.query(AuditEvent).count()

    # Se agrega un evento nuevo ("eliminar_importacion"), y ninguno de los viejos se borra
    assert eventos_despues == eventos_antes + 1
    assert all(e.import_batch_id is None for e in db_session.query(AuditEvent).all())


def test_merge_providers_reasigna_facturas_y_alias(db_session, admin_user, seeded_catalogs):
    batch = process_uploaded_file(db_session, admin_user.id, "tsdocs_sample.csv", _load_fixture_bytes())
    approve_pending_in_batch(db_session, batch, admin_user.id)

    target = db_session.query(Provider).first()
    otro = Provider(nombre_normalizado="Proveedor Duplicado SA")
    db_session.add(otro)
    db_session.flush()
    db_session.add(ProviderAlias(provider_id=otro.id, alias_texto="Alias del duplicado"))
    db_session.commit()

    # Movemos a mano una factura al proveedor "duplicado" para simular el caso real
    factura = db_session.query(Invoice).first()
    factura.provider_id = otro.id
    db_session.commit()

    resultado = merge_providers(db_session, target, otro, admin_user.id)

    assert resultado["facturas_reasignadas"] == 1
    assert resultado["alias_reasignados"] == 1
    db_session.refresh(factura)
    assert factura.provider_id == target.id
    assert db_session.query(Provider).filter(Provider.id == otro.id).first() is None
    # El nombre del proveedor descartado queda como alias del que sobrevive
    assert any(a.alias_texto == "Proveedor Duplicado SA" for a in target.aliases)


def test_merge_providers_no_permite_fusionar_consigo_mismo(db_session, admin_user, seeded_catalogs):
    provider = Provider(nombre_normalizado="Solo")
    db_session.add(provider)
    db_session.commit()

    import pytest
    with pytest.raises(ValueError):
        merge_providers(db_session, provider, provider, admin_user.id)
