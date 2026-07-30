"""
Calculos de reportes y dashboard (secciones 11 y 12 del diseño).

Regla de signo (addendum #15 del documento de diseño): al sumar gasto,
Factura y Factura de Credito Pyme suman, Nota de Credito resta, Nota de
Debito suma -- asi el "gasto real" ya queda neto de devoluciones/ajustes.

Solo se consideran facturas en pesos (moneda in Pesos/ARS): es la moneda
base decidida para el MVP: no hay conversion de USD sin una tabla de tipo
de cambio (decision ya tomada: se elimino exchange_rates).
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.invoicing import Invoice
from app.models.catalog import Provider, ExpenseCategory, Area
from app.models.budget import Budget
from app.models.importing import ImportBatch, StagingInvoice

MONEDAS_BASE = ("Pesos", "ARS")
NOTAS_QUE_RESTAN = {"Nota Credito", "Nota de Credito"}


def signo(tipo_documento: str | None) -> int:
    return -1 if (tipo_documento or "").strip() in NOTAS_QUE_RESTAN else 1


def _invoices_query(db: Session, anio: int, mes: int | None = None):
    q = db.query(Invoice).filter(
        Invoice.estado == "aprobado",
        Invoice.moneda.in_(MONEDAS_BASE),
        func.extract("year", Invoice.fecha_emision) == anio,
    )
    if mes:
        q = q.filter(func.extract("month", Invoice.fecha_emision) == mes)
    return q


def gasto_neto(invoices: list[Invoice]) -> Decimal:
    total = Decimal(0)
    for inv in invoices:
        total += signo(inv.tipo_documento) * (inv.importe_total or Decimal(0))
    return total


def default_periodo(db: Session) -> tuple[int, int]:
    """Ultimo mes con facturas aprobadas; si no hay ninguna, el mes actual."""
    ultima_fecha = db.query(func.max(Invoice.fecha_emision)).filter(Invoice.estado == "aprobado").scalar()
    if ultima_fecha:
        return ultima_fecha.year, ultima_fecha.month
    now = datetime.utcnow()
    return now.year, now.month


def presupuesto_mensual_total(db: Session, anio: int) -> Decimal:
    rows = db.query(Budget).filter(Budget.anio == anio, Budget.importe_mensual_equivalente.isnot(None)).all()
    return sum((b.importe_mensual_equivalente for b in rows), Decimal(0))


def dashboard_kpis(db: Session, anio: int, mes: int) -> dict:
    facturas_mes = _invoices_query(db, anio, mes).all()
    gasto_mes = gasto_neto(facturas_mes)

    facturas_anio_hasta_mes = db.query(Invoice).filter(
        Invoice.estado == "aprobado",
        Invoice.moneda.in_(MONEDAS_BASE),
        func.extract("year", Invoice.fecha_emision) == anio,
        func.extract("month", Invoice.fecha_emision) <= mes,
    ).all()
    gasto_acumulado_anio = gasto_neto(facturas_anio_hasta_mes)

    presupuesto_mensual = presupuesto_mensual_total(db, anio)
    presupuesto_anual = presupuesto_mensual * 12

    mes_anterior = 12 if mes == 1 else mes - 1
    anio_mes_anterior = anio - 1 if mes == 1 else anio
    facturas_mes_anterior = _invoices_query(db, anio_mes_anterior, mes_anterior).all()
    gasto_mes_anterior = gasto_neto(facturas_mes_anterior)
    variacion_mes_anterior_pct = (
        float((gasto_mes - gasto_mes_anterior) / gasto_mes_anterior * 100) if gasto_mes_anterior else None
    )

    facturas_mismo_mes_anio_anterior = _invoices_query(db, anio - 1, mes).all()
    gasto_mismo_mes_anio_anterior = gasto_neto(facturas_mismo_mes_anio_anterior)
    variacion_interanual_pct = (
        float((gasto_mes - gasto_mismo_mes_anio_anterior) / gasto_mismo_mes_anio_anterior * 100)
        if gasto_mismo_mes_anio_anterior else None
    )

    proyeccion_cierre_anio = float(gasto_acumulado_anio / mes * 12) if mes else None

    cantidad_proveedores = len({f.provider_id for f in facturas_mes if f.provider_id})
    importaciones_pendientes = db.query(func.count(ImportBatch.id)).filter(
        ImportBatch.estado.in_(["pendiente_validacion", "con_errores"])
    ).scalar()
    registros_con_error = db.query(func.count(StagingInvoice.id)).filter(
        StagingInvoice.estado_fila == "error", StagingInvoice.resultado == "pendiente"
    ).scalar()

    return {
        "anio": anio,
        "mes": mes,
        "gasto_total_mes": float(gasto_mes),
        "gasto_acumulado_anio": float(gasto_acumulado_anio),
        "presupuesto_mensual": float(presupuesto_mensual),
        "presupuesto_anual": float(presupuesto_anual),
        "porcentaje_consumido_mes": float(gasto_mes / presupuesto_mensual * 100) if presupuesto_mensual else None,
        "desvio_contra_presupuesto_mes": float(gasto_mes - presupuesto_mensual),
        "proyeccion_cierre_anio": proyeccion_cierre_anio,
        "variacion_mes_anterior_pct": variacion_mes_anterior_pct,
        "variacion_interanual_pct": variacion_interanual_pct,
        "cantidad_facturas_mes": len(facturas_mes),
        "cantidad_proveedores_mes": cantidad_proveedores,
        "importaciones_pendientes": importaciones_pendientes or 0,
        "registros_con_error": registros_con_error or 0,
    }


def evolucion_mensual(db: Session, anio: int) -> list[dict]:
    resultado = []
    for mes in range(1, 13):
        facturas = _invoices_query(db, anio, mes).all()
        resultado.append({"mes": mes, "gasto": float(gasto_neto(facturas))})
    return resultado


def _ranking_generico(db: Session, anio: int, mes: int | None, agrupar_por: str) -> list[dict]:
    facturas = _invoices_query(db, anio, mes).all()
    totales: dict[int, Decimal] = {}
    for f in facturas:
        clave = getattr(f, agrupar_por)
        if clave is None:
            continue
        totales[clave] = totales.get(clave, Decimal(0)) + signo(f.tipo_documento) * (f.importe_total or Decimal(0))

    total_general = sum(totales.values(), Decimal(0))
    filas = sorted(totales.items(), key=lambda kv: -kv[1])

    resultado = []
    acumulado = Decimal(0)
    for clave, monto in filas:
        acumulado += monto
        resultado.append({
            "id": clave,
            "monto": float(monto),
            "participacion_pct": float(monto / total_general * 100) if total_general else 0.0,
            "acumulado_pct": float(acumulado / total_general * 100) if total_general else 0.0,
        })
    return resultado


def ranking_por_proveedor(db: Session, anio: int, mes: int | None = None) -> list[dict]:
    filas = _ranking_generico(db, anio, mes, "provider_id")
    for f in filas:
        p = db.query(Provider).filter(Provider.id == f["id"]).first()
        f["nombre"] = p.nombre_normalizado if p else "?"
        f["provider_id"] = f.pop("id")
    return filas


def ranking_por_categoria(db: Session, anio: int, mes: int | None = None) -> list[dict]:
    filas = _ranking_generico(db, anio, mes, "category_id")
    for f in filas:
        c = db.query(ExpenseCategory).filter(ExpenseCategory.id == f["id"]).first()
        f["nombre"] = c.nombre if c else "?"
        f["category_id"] = f.pop("id")
    return filas


def ranking_por_area(db: Session, anio: int, mes: int | None = None) -> list[dict]:
    filas = _ranking_generico(db, anio, mes, "area_id")
    for f in filas:
        a = db.query(Area).filter(Area.id == f["id"]).first()
        f["nombre"] = a.nombre_normalizado if a else "?"
        f["area_id"] = f.pop("id")
    return filas
