"""
Calculos de reportes y dashboard (secciones 11 y 12 del diseño).

Trabaja sobre un RANGO DE FECHAS libre (fecha_desde/fecha_hasta), no solo
"año/mes fijo" -- para poder pedir un mes especifico, un semestre, un año
completo, o cualquier corte parcial una vez que se carguen historicos.

Regla de signo (addendum #15 del documento de diseño): al sumar gasto,
Factura y Factura de Credito Pyme suman, Nota de Credito resta, Nota de
Debito suma -- asi el "gasto real" ya queda neto de devoluciones/ajustes.

Solo se consideran facturas en pesos (moneda in Pesos/ARS): es la moneda
base decidida para el MVP: no hay conversion de USD sin una tabla de tipo
de cambio (decision ya tomada: se elimino exchange_rates).
"""
import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.invoicing import Invoice
from app.models.catalog import Provider, ExpenseCategory, Area, Company
from app.models.budget import Budget
from app.models.importing import ImportBatch, StagingInvoice

MONEDAS_BASE = ("Pesos", "ARS")
NOTAS_QUE_RESTAN = {"Nota Credito", "Nota de Credito"}
DIAS_PROMEDIO_MES = Decimal("30.44")  # 365.25 / 12, para prorratear presupuesto mensual a cualquier rango


def signo(tipo_documento: str | None) -> int:
    return -1 if (tipo_documento or "").strip() in NOTAS_QUE_RESTAN else 1


def _invoices_query_rango(db: Session, fecha_desde: date, fecha_hasta: date, economic_group_id: int | None = None):
    q = db.query(Invoice).filter(
        Invoice.estado == "aprobado",
        Invoice.moneda.in_(MONEDAS_BASE),
        Invoice.fecha_emision >= fecha_desde,
        Invoice.fecha_emision <= datetime.combine(fecha_hasta, datetime.max.time()),
    )
    if economic_group_id:
        q = q.join(Company, Company.id == Invoice.company_id).filter(Company.economic_group_id == economic_group_id)
    return q


def gasto_neto(invoices: list[Invoice]) -> Decimal:
    total = Decimal(0)
    for inv in invoices:
        total += signo(inv.tipo_documento) * (inv.importe_total or Decimal(0))
    return total


def default_rango(db: Session) -> tuple[date, date]:
    """Por defecto: el ultimo mes calendario que tenga alguna factura aprobada."""
    ultima_fecha = db.query(Invoice.fecha_emision).filter(Invoice.estado == "aprobado").order_by(Invoice.fecha_emision.desc()).first()
    if ultima_fecha and ultima_fecha[0]:
        ref = ultima_fecha[0].date()
    else:
        ref = datetime.utcnow().date()
    desde = ref.replace(day=1)
    ultimo_dia = calendar.monthrange(ref.year, ref.month)[1]
    hasta = ref.replace(day=ultimo_dia)
    return desde, hasta


def presupuesto_mensual_total(db: Session, anio: int) -> Decimal:
    rows = db.query(Budget).filter(Budget.anio == anio, Budget.importe_mensual_equivalente.isnot(None)).all()
    return sum((b.importe_mensual_equivalente for b in rows), Decimal(0))


def presupuesto_prorrateado(db: Session, fecha_desde: date, fecha_hasta: date) -> Decimal:
    """
    El presupuesto se guarda como un valor MENSUAL (importe_mensual_equivalente).
    Para compararlo contra un rango arbitrario (una semana, un semestre, un año),
    se prorratea por cantidad de dias: dias_del_rango / 30.44 (promedio real de
    dias por mes) * presupuesto mensual. Si el rango cruza más de un año
    calendario, se promedia el presupuesto mensual total de cada año involucrado.
    """
    dias = (fecha_hasta - fecha_desde).days + 1
    anios = list(range(fecha_desde.year, fecha_hasta.year + 1))
    if not anios:
        return Decimal(0)
    totales_por_anio = [presupuesto_mensual_total(db, a) for a in anios]
    promedio_mensual = sum(totales_por_anio, Decimal(0)) / len(anios)
    return promedio_mensual * Decimal(dias) / DIAS_PROMEDIO_MES


def _periodo_anterior_equivalente(fecha_desde: date, fecha_hasta: date) -> tuple[date, date]:
    """El mismo largo de dias, inmediatamente antes del rango elegido."""
    dias = (fecha_hasta - fecha_desde).days + 1
    anterior_hasta = fecha_desde - timedelta(days=1)
    anterior_desde = anterior_hasta - timedelta(days=dias - 1)
    return anterior_desde, anterior_hasta


def dashboard_kpis(db: Session, fecha_desde: date, fecha_hasta: date, economic_group_id: int | None = None) -> dict:
    facturas = _invoices_query_rango(db, fecha_desde, fecha_hasta, economic_group_id).all()
    gasto_total = gasto_neto(facturas)

    anterior_desde, anterior_hasta = _periodo_anterior_equivalente(fecha_desde, fecha_hasta)
    facturas_anterior = _invoices_query_rango(db, anterior_desde, anterior_hasta, economic_group_id).all()
    gasto_anterior = gasto_neto(facturas_anterior)
    variacion_pct = (
        float((gasto_total - gasto_anterior) / gasto_anterior * 100) if gasto_anterior else None
    )

    presupuesto_periodo = presupuesto_prorrateado(db, fecha_desde, fecha_hasta)

    cantidad_proveedores = len({f.provider_id for f in facturas if f.provider_id})
    importaciones_pendientes = db.query(ImportBatch).filter(
        ImportBatch.estado.in_(["pendiente_validacion", "con_errores"])
    ).count()
    registros_con_error = db.query(StagingInvoice).filter(
        StagingInvoice.estado_fila == "error", StagingInvoice.resultado == "pendiente"
    ).count()

    dias = (fecha_hasta - fecha_desde).days + 1

    return {
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "dias": dias,
        "gasto_total_periodo": float(gasto_total),
        "presupuesto_periodo": float(presupuesto_periodo),
        "porcentaje_consumido": float(gasto_total / presupuesto_periodo * 100) if presupuesto_periodo else None,
        "desvio_contra_presupuesto": float(gasto_total - presupuesto_periodo),
        "variacion_vs_periodo_anterior_pct": variacion_pct,
        "cantidad_facturas": len(facturas),
        "cantidad_proveedores": cantidad_proveedores,
        "importaciones_pendientes": importaciones_pendientes,
        "registros_con_error": registros_con_error,
    }


def evolucion_mensual(db: Session, fecha_desde: date, fecha_hasta: date, economic_group_id: int | None = None) -> list[dict]:
    """Un punto por cada mes calendario que el rango toca (puede cruzar años)."""
    resultado = []
    cursor = fecha_desde.replace(day=1)
    while cursor <= fecha_hasta:
        ultimo_dia = calendar.monthrange(cursor.year, cursor.month)[1]
        inicio_mes = max(cursor, fecha_desde)
        fin_mes = min(cursor.replace(day=ultimo_dia), fecha_hasta)
        facturas = _invoices_query_rango(db, inicio_mes, fin_mes, economic_group_id).all()
        resultado.append({"anio": cursor.year, "mes": cursor.month, "gasto": float(gasto_neto(facturas))})

        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return resultado


def _ranking_generico(db: Session, fecha_desde: date, fecha_hasta: date, agrupar_por: str, economic_group_id: int | None = None) -> list[dict]:
    facturas = _invoices_query_rango(db, fecha_desde, fecha_hasta, economic_group_id).all()
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


def ranking_por_proveedor(db: Session, fecha_desde: date, fecha_hasta: date, economic_group_id: int | None = None) -> list[dict]:
    filas = _ranking_generico(db, fecha_desde, fecha_hasta, "provider_id", economic_group_id)
    for f in filas:
        p = db.query(Provider).filter(Provider.id == f["id"]).first()
        f["nombre"] = p.nombre_normalizado if p else "?"
        f["provider_id"] = f.pop("id")
    return filas


def ranking_por_categoria(db: Session, fecha_desde: date, fecha_hasta: date, economic_group_id: int | None = None) -> list[dict]:
    filas = _ranking_generico(db, fecha_desde, fecha_hasta, "category_id", economic_group_id)
    for f in filas:
        c = db.query(ExpenseCategory).filter(ExpenseCategory.id == f["id"]).first()
        f["nombre"] = c.nombre if c else "?"
        f["category_id"] = f.pop("id")
    return filas


def ranking_por_area(db: Session, fecha_desde: date, fecha_hasta: date, economic_group_id: int | None = None) -> list[dict]:
    filas = _ranking_generico(db, fecha_desde, fecha_hasta, "area_id", economic_group_id)
    for f in filas:
        a = db.query(Area).filter(Area.id == f["id"]).first()
        f["nombre"] = a.nombre_normalizado if a else "?"
        f["area_id"] = f.pop("id")
    return filas
