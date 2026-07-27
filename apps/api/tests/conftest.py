"""
Fixtures compartidas para los tests. Usa SQLite en memoria (no Postgres),
suficiente para probar la logica de negocio sin depender de una base real.
Las columnas JSON usan un tipo con variante (JSON generico / JSONB en Postgres),
por eso todas las tablas se pueden crear en SQLite sin exclusiones.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.core.security import hash_password
from app.models.security import Role, User, UserRole
import app.models  # noqa: F401  (asegura que todos los modelos esten registrados)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def admin_user(db_session):
    role = Role(nombre="Administrador")
    db_session.add(role)
    db_session.flush()

    user = User(
        email="admin@test.com",
        nombre="Admin Test",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    db_session.commit()
    return user


@pytest.fixture()
def seeded_catalogs(db_session):
    """Siembra categorias/centros de costo ST0x reutilizando scripts/seed.py (una sola fuente de verdad)."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.seed import seed_categorias, seed_centros_costo

    seed_categorias(db_session)
    seed_centros_costo(db_session)
    db_session.commit()
