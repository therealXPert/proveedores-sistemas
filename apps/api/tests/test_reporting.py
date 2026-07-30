"""
Tests de la logica pura de reportes (signo por tipo de documento, gasto neto).
Las consultas que agrupan por fecha (evolucion mensual, rankings) se probaron
a mano contra Postgres real con los 3 archivos reales + presupuesto real
(ver README de la etapa) -- no se repiten aca porque dependen de func.extract,
que no se comporta igual en SQLite que en Postgres.
"""
from decimal import Decimal
from types import SimpleNamespace

from app.services.reporting_service import signo, gasto_neto


def _factura(tipo, importe):
    return SimpleNamespace(tipo_documento=tipo, importe_total=Decimal(str(importe)))


def test_signo_factura_suma():
    assert signo("Factura") == 1


def test_signo_nota_credito_resta():
    assert signo("Nota Credito") == -1
    assert signo("Nota de Credito") == -1


def test_signo_nota_debito_suma():
    assert signo("Nota Debito") == 1


def test_signo_factura_credito_pyme_suma():
    assert signo("Factura de Credito Pyme") == 1


def test_signo_valor_vacio_suma_por_default():
    assert signo(None) == 1
    assert signo("") == 1


def test_gasto_neto_resta_notas_de_credito():
    facturas = [
        _factura("Factura", 1000),
        _factura("Factura", 500),
        _factura("Nota Credito", 200),
        _factura("Nota Debito", 50),
    ]
    # 1000 + 500 - 200 + 50 = 1350
    assert gasto_neto(facturas) == Decimal("1350")


def test_gasto_neto_lista_vacia_es_cero():
    assert gasto_neto([]) == Decimal("0")
