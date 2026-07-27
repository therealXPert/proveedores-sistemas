"""Pruebas basicas del modelo de datos: que los catalogos y sus relaciones funcionen."""
from app.models.catalog import Area, ExpenseCategory, CostCenter, BusinessUnit, Provider, ProviderAlias


def test_create_area(db_session):
    area = Area(nombre_normalizado="Sistemas Mesa de Servicio")
    db_session.add(area)
    db_session.commit()
    assert db_session.query(Area).count() == 1


def test_expense_category_hierarchy(db_session):
    padre = ExpenseCategory(nombre="Sistemas Inversiones", codigo_erp=None)
    db_session.add(padre)
    db_session.flush()

    hijo = ExpenseCategory(nombre="Sistemas Inversiones - Equipos", codigo_erp="STI06", categoria_padre_id=padre.id)
    db_session.add(hijo)
    db_session.commit()

    assert hijo.categoria_padre_id == padre.id


def test_provider_with_aliases(db_session):
    provider = Provider(nombre_normalizado="Google Cloud")
    db_session.add(provider)
    db_session.flush()

    db_session.add(ProviderAlias(provider_id=provider.id, alias_texto="Google"))
    db_session.add(ProviderAlias(provider_id=provider.id, alias_texto="Google LLC"))
    db_session.commit()

    db_session.refresh(provider)
    assert len(provider.aliases) == 2


def test_business_unit_seed_like_creation(db_session):
    for nombre in ["Sistemas", "Comercial", "Marketing"]:
        db_session.add(BusinessUnit(nombre=nombre))
    db_session.commit()
    assert db_session.query(BusinessUnit).count() == 3


def test_cost_center_unique_codigo(db_session):
    db_session.add(CostCenter(codigo="ST07", nombre="Licencias"))
    db_session.commit()
    cc = db_session.query(CostCenter).filter_by(codigo="ST07").first()
    assert cc.nombre == "Licencias"
