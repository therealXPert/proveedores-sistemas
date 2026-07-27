"""
Script de semillas para el MVP: roles, usuario administrador inicial, y catalogos
base (areas, categorias, centros de costo, unidades de negocio) tomados de los
datos reales analizados en el documento de diseño (Presupuesto_Sistemas.xlsx y
los CSV/XLSX de TSDocs).

Uso:
    python -m scripts.seed --admin-email diego@autocity.com --admin-password "CAMBIAR"

Es seguro correrlo mas de una vez: no duplica filas si ya existen (usa get_or_create).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.core.security import hash_password
from app.models.security import Role, User, UserRole
from app.models.catalog import Area, ExpenseCategory, CostCenter, BusinessUnit

ROLES = ["Administrador", "Analista", "Consulta"]

AREAS = [
    "Sistemas Aplicaciones Negocio",
    "Sistemas Mesa de Servicio",
    "Sistemas Tecnologia y Operaciones",
]

# (nombre categoria, codigo_erp) - tomado de 'Cuenta Personal' en los CSV/XLSX reales
CATEGORIAS = [
    ("Sueldos", "ST01"),
    ("Viaticos y Gastos al Personal", "ST02"),
    ("Otros Servicios", "ST03"),
    ("Data Center", "ST04"),
    ("Desarrollo de Software", "ST05"),
    ("Equipos de Computacion", "ST06"),
    ("Licencias", "ST07"),
    ("Telefonia y Comunicaciones", "ST08"),
    ("Sistemas Inversiones - Otros Servicios", "STI03"),
    ("Sistemas Inversiones - Desarrollo Software", "STI05"),
    ("Sistemas Inversiones - Equipos de Computacion", "STI06"),
]

# Los centros de costo ERP usan el mismo codigo que la categoria (1 a 1, ver addendum #4/13
# del documento de diseño: "Cuenta Personal" se parsea en Categoria + Centro de Costo)
CENTROS_COSTO = [(codigo, nombre) for nombre, codigo in CATEGORIAS]

BUSINESS_UNITS = [
    "Sistemas",
    "Comercial",
    "Marketing",
    "RRHH",
    "Adm & Fin",
    "Logistica",
    "Seguridad",
    "Contact Center",
    "Gestoria",
]


def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance, True


def seed_roles(db):
    roles = {}
    for nombre in ROLES:
        role, created = get_or_create(db, Role, nombre=nombre)
        roles[nombre] = role
        print(f"{'Creado' if created else 'Ya existia'}: rol '{nombre}'")
    return roles


def seed_areas(db):
    for nombre in AREAS:
        _, created = get_or_create(db, Area, nombre_normalizado=nombre)
        print(f"{'Creada' if created else 'Ya existia'}: area '{nombre}'")


def seed_categorias(db):
    for nombre, codigo in CATEGORIAS:
        _, created = get_or_create(db, ExpenseCategory, nombre=nombre, codigo_erp=codigo)
        print(f"{'Creada' if created else 'Ya existia'}: categoria '{nombre}' ({codigo})")


def seed_centros_costo(db):
    for codigo, nombre in CENTROS_COSTO:
        _, created = get_or_create(db, CostCenter, codigo=codigo, defaults={"nombre": nombre})
        print(f"{'Creado' if created else 'Ya existia'}: centro de costo '{codigo}' - {nombre}")


def seed_business_units(db):
    for nombre in BUSINESS_UNITS:
        _, created = get_or_create(db, BusinessUnit, nombre=nombre)
        print(f"{'Creada' if created else 'Ya existia'}: unidad de negocio '{nombre}'")


def seed_admin_user(db, roles, email: str, password: str, nombre: str = "Administrador"):
    user, created = get_or_create(
        db,
        User,
        email=email,
        defaults={"nombre": nombre, "password_hash": hash_password(password)},
    )
    if not created:
        print(f"Ya existia el usuario '{email}', no se modifica la contraseña.")
    else:
        print(f"Creado usuario administrador '{email}'.")

    existing = db.query(UserRole).filter_by(user_id=user.id, role_id=roles["Administrador"].id).first()
    if not existing:
        db.add(UserRole(user_id=user.id, role_id=roles["Administrador"].id))
        print("Rol 'Administrador' asignado.")


def main():
    parser = argparse.ArgumentParser(description="Semillas iniciales del MVP")
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--admin-nombre", default="Administrador")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        roles = seed_roles(db)
        seed_areas(db)
        seed_categorias(db)
        seed_centros_costo(db)
        seed_business_units(db)
        seed_admin_user(db, roles, args.admin_email, args.admin_password, args.admin_nombre)
        db.commit()
        print("\nSemillas aplicadas correctamente.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
