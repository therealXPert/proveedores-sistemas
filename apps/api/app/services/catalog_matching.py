"""
Normalizacion de las dimensiones simples: Area, Empresa, Sucursal (sección 9 y
addendum #14 del diseño). Mismo patron que providers: match por alias exacto,
si no existe se crea (sin bloquear la carga). Ademas, el parseo de 'Cuenta
Personal' en Categoria + Centro de Costo ERP (addendum #4/13).
"""
import re

from sqlalchemy.orm import Session

from app.models.catalog import Area, AreaAlias, Company, Branch, ExpenseCategory, CostCenter


def get_or_create_area(db: Session, area_raw: str | None) -> Area | None:
    if not area_raw:
        return None
    texto = area_raw.strip()
    if not texto:
        return None

    alias = db.query(AreaAlias).filter(AreaAlias.alias_texto == texto).first()
    if alias:
        return alias.area

    area = db.query(Area).filter(Area.nombre_normalizado == texto).first()
    if not area:
        area = Area(nombre_normalizado=texto)
        db.add(area)
        db.flush()

    db.add(AreaAlias(area_id=area.id, alias_texto=texto))
    return area


def get_or_create_company(db: Session, nombre_raw: str | None) -> Company | None:
    if not nombre_raw or not nombre_raw.strip():
        return None
    nombre = nombre_raw.strip()
    company = db.query(Company).filter(Company.nombre == nombre).first()
    if not company:
        company = Company(nombre=nombre)
        db.add(company)
        db.flush()
    return company


def get_or_create_branch(db: Session, nombre_raw: str | None) -> Branch | None:
    if not nombre_raw or not nombre_raw.strip():
        return None
    nombre = nombre_raw.strip()
    branch = db.query(Branch).filter(Branch.nombre == nombre).first()
    if not branch:
        branch = Branch(nombre=nombre)
        db.add(branch)
        db.flush()
    return branch


# 'SISTEMAS - LICENCIAS SISTEMAS - ST07' -> grupo='SISTEMAS', descripcion='LICENCIAS SISTEMAS', codigo='ST07'
CUENTA_PERSONAL_PATTERN = re.compile(r"^(.*?)\s-\s(.*?)\s-\s([A-Z]+\d+)\s*$")


def parse_cuenta_personal(cuenta_personal_raw: str | None) -> tuple[str | None, str | None, str | None]:
    if not cuenta_personal_raw:
        return None, None, None
    match = CUENTA_PERSONAL_PATTERN.match(cuenta_personal_raw.strip())
    if not match:
        return None, None, cuenta_personal_raw.strip() or None
    grupo, descripcion, codigo = match.groups()
    return grupo.strip(), descripcion.strip(), codigo.strip()


def get_category_and_cost_center(
    db: Session, cuenta_personal_raw: str | None
) -> tuple[ExpenseCategory | None, CostCenter | None, str | None]:
    """
    Devuelve (categoria, centro_de_costo, advertencia). 'advertencia' es un texto
    para dejar como validation_error de tipo 'advertencia' si el codigo no esta
    en el catalogo seedeado (ver scripts/seed.py) -- no bloquea la carga.
    """
    _, _, codigo = parse_cuenta_personal(cuenta_personal_raw)
    if not codigo:
        return None, None, f"No se pudo interpretar 'Cuenta Personal': '{cuenta_personal_raw}'"

    cost_center = db.query(CostCenter).filter(CostCenter.codigo == codigo).first()
    category = db.query(ExpenseCategory).filter(ExpenseCategory.codigo_erp == codigo).first()

    if not cost_center or not category:
        return category, cost_center, f"Codigo de Cuenta Personal no reconocido: '{codigo}'"

    return category, cost_center, None
