"""
Carga el presupuesto real desde Presupuesto_Sistemas.xlsx.

Uso:
    python -m scripts.import_budget /ruta/a/Presupuesto_Sistemas.xlsx --anio 2026

Es seguro correrlo mas de una vez SOLO si primero se borra la version anterior
a mano (no hay deduplicacion de filas de presupuesto todavia) -- pensado para
una carga inicial unica.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.models.budget import BudgetVersion
from app.services.budget_import_service import import_presupuesto_sistemas


def get_or_create_version(db, nombre: str, tipo: str):
    version = db.query(BudgetVersion).filter(BudgetVersion.nombre == nombre).first()
    if version:
        return version, False
    version = BudgetVersion(nombre=nombre, tipo=tipo)
    db.add(version)
    db.flush()
    return version, True


def main():
    parser = argparse.ArgumentParser(description="Importar Presupuesto_Sistemas.xlsx")
    parser.add_argument("archivo")
    parser.add_argument("--anio", type=int, default=2026)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        nombre_version = f"Presupuesto {args.anio} - vigente"
        version, creada = get_or_create_version(db, nombre_version, "vigente")
        db.commit()
        print(f"{'Creada' if creada else 'Ya existía'} versión de presupuesto: '{version.nombre}' (id={version.id})")

        content = Path(args.archivo).read_bytes()
        resultado = import_presupuesto_sistemas(db, content, version, anio=args.anio)

        print("\nResultado de la importación:")
        for k, v in resultado.items():
            print(f"  {k}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
