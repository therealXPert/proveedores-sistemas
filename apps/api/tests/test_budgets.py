"""Tests del modulo de presupuesto: normalizacion de periodicidad y CRUD basico."""
from decimal import Decimal

from app.services.budget_import_service import _periodicidad_a_mensual, _normalize_area
from app.models.budget import Budget, BudgetVersion
from app.models.catalog import Provider


def test_periodicidad_mensual_no_cambia():
    assert _periodicidad_a_mensual(Decimal("1000"), "Mensual") == Decimal("1000")


def test_periodicidad_bimensual_se_divide_por_2():
    assert _periodicidad_a_mensual(Decimal("1000"), "Bimensual") == Decimal("500")


def test_periodicidad_trimestral_se_divide_por_3():
    assert _periodicidad_a_mensual(Decimal("900"), "Trimestral") == Decimal("300")


def test_periodicidad_a_demanda_no_tiene_equivalente_mensual():
    assert _periodicidad_a_mensual(Decimal("1000"), "A demanda") is None


def test_periodicidad_sin_importe_devuelve_none():
    assert _periodicidad_a_mensual(None, "Mensual") is None


def test_normalize_area_apn():
    assert _normalize_area("APN") == ("Sistemas Aplicaciones Negocio", None)


def test_normalize_area_multivalor_no_se_reparte():
    nombre, original = _normalize_area("Mesa de Servicio, Tecnologia")
    assert nombre is None
    assert original == "Mesa de Servicio, Tecnologia"


def test_normalize_area_vacia():
    assert _normalize_area(None) == (None, None)


def test_crear_y_editar_presupuesto(db_session, admin_user, seeded_catalogs):
    provider = Provider(nombre_normalizado="Proveedor Test")
    db_session.add(provider)
    db_session.flush()

    version = BudgetVersion(nombre="Presupuesto 2026 - vigente", tipo="vigente")
    db_session.add(version)
    db_session.flush()

    budget = Budget(
        budget_version_id=version.id,
        anio=2026,
        provider_id=provider.id,
        moneda="ARS",
        periodicidad_original="Mensual",
        importe_original=Decimal("1000"),
        importe_mensual_equivalente=Decimal("1000"),
    )
    db_session.add(budget)
    db_session.commit()

    assert db_session.query(Budget).count() == 1

    # Editar: cambia importe y periodicidad -> se recalcula el mensual equivalente
    budget.importe_original = Decimal("3000")
    budget.periodicidad_original = "Trimestral"
    budget.importe_mensual_equivalente = _periodicidad_a_mensual(budget.importe_original, budget.periodicidad_original)
    db_session.commit()

    assert budget.importe_mensual_equivalente == Decimal("1000")
