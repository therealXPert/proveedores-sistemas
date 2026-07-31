"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api, DashboardKPIs, RankingItem, ApiError, downloadFile } from "@/lib/api";
import DateRangePicker, { Rango } from "@/components/DateRangePicker";

const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const COLORS = ["#e0a339", "#5b8fb0", "#4f9d6e", "#d9636f", "#8fa0ac", "#7a5a24"];

function formatMonto(n: number) {
  return n.toLocaleString("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatFechaCorta(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" });
}

function Pct({ value }: { value: number | null }) {
  if (value === null) return <span className="faint">—</span>;
  const color = value > 0 ? "var(--error)" : "var(--ok)";
  return <span style={{ color }}>{value > 0 ? "+" : ""}{value.toFixed(1)}%</span>;
}

export default function DashboardPage() {
  const [rango, setRango] = useState<Rango | null>(null);
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [evolucion, setEvolucion] = useState<{ anio: number; mes: number; gasto: number }[] | null>(null);
  const [porProveedor, setPorProveedor] = useState<RankingItem[] | null>(null);
  const [porArea, setPorArea] = useState<RankingItem[] | null>(null);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Al entrar, sin fechas: el backend elige el ultimo mes con datos. Una vez que
  // sabemos cual es, lo usamos como "referencia" para que los atajos (Este mes,
  // Este año) tengan sentido incluso si "hoy" todavia no tiene facturas cargadas.
  useEffect(() => {
    (async () => {
      try {
        const k = await api.dashboard();
        setKpis(k);
        setRango({ desde: k.fecha_desde, hasta: k.fecha_hasta });
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard.");
      }
    })();
  }, []);

  useEffect(() => {
    if (!rango) return;
    setError(null);
    (async () => {
      try {
        const [k, evo, prov, area] = await Promise.all([
          api.dashboard(rango.desde, rango.hasta),
          api.evolucionMensual(rango.desde, rango.hasta),
          api.rankingProveedores(rango.desde, rango.hasta),
          api.rankingAreas(rango.desde, rango.hasta),
        ]);
        setKpis(k);
        setEvolucion(evo);
        setPorProveedor(prov.slice(0, 8));
        setPorArea(area);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard.");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rango?.desde, rango?.hasta]);

  async function handleExportPdf() {
    if (!rango) return;
    setExportando(true);
    setError(null);
    try {
      await downloadFile(
        `/dashboard/export-pdf?fecha_desde=${rango.desde}&fecha_hasta=${rango.hasta}`,
        `informe-ejecutivo-${rango.desde}_a_${rango.hasta}.pdf`
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo generar el informe.");
    } finally {
      setExportando(false);
    }
  }

  if (error) return <div className="error-banner">{error}</div>;
  if (!kpis || !rango || !evolucion || !porProveedor || !porArea) return <div className="muted">Cargando...</div>;

  const evolucionData = evolucion.map((e) => ({
    etiqueta: `${MESES[e.mes - 1]} ${String(e.anio).slice(2)}`,
    gasto: e.gasto,
  }));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            Sistemas · {formatFechaCorta(kpis.fecha_desde)} — {formatFechaCorta(kpis.fecha_hasta)} ({kpis.dias} días)
          </div>
          <h1 className="h1">Dashboard ejecutivo</h1>
        </div>
        <button className="btn btn-primary" onClick={handleExportPdf} disabled={exportando}>
          {exportando ? "Generando..." : "Descargar informe PDF"}
        </button>
      </div>

      <div style={{ marginBottom: 24 }}>
        <DateRangePicker value={rango} onChange={setRango} referencia={new Date(kpis.fecha_hasta + "T00:00:00")} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
        <KpiCard label="Gasto del período" value={formatMonto(kpis.gasto_total_periodo)} sub={<>vs. período anterior equivalente <Pct value={kpis.variacion_vs_periodo_anterior_pct} /></>} />
        <KpiCard label="Presupuesto del período" value={formatMonto(kpis.presupuesto_periodo)} sub="Prorrateado por días" />
        <KpiCard
          label="% presupuesto consumido"
          value={kpis.porcentaje_consumido !== null ? `${kpis.porcentaje_consumido.toFixed(0)}%` : "—"}
          sub={<>Desvío: <span style={{ color: kpis.desvio_contra_presupuesto > 0 ? "var(--error)" : "var(--ok)" }}>{formatMonto(kpis.desvio_contra_presupuesto)}</span></>}
          color={kpis.porcentaje_consumido && kpis.porcentaje_consumido > 100 ? "var(--error)" : "var(--text)"}
        />
        <KpiCard label="Facturas del período" value={String(kpis.cantidad_facturas)} sub={`${kpis.cantidad_proveedores} proveedores`} />
      </div>

      {(kpis.importaciones_pendientes > 0 || kpis.registros_con_error > 0) && (
        <div className="card" style={{ padding: "12px 16px", marginBottom: 24, borderColor: "var(--warn)", display: "flex", gap: 24 }}>
          {kpis.importaciones_pendientes > 0 && (
            <span style={{ fontSize: 13, color: "var(--warn)" }}>⚠ {kpis.importaciones_pendientes} importación(es) pendiente(s) de validación</span>
          )}
          {kpis.registros_con_error > 0 && (
            <span style={{ fontSize: 13, color: "var(--error)" }}>⚠ {kpis.registros_con_error} factura(s) con error sin resolver</span>
          )}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, marginBottom: 20 }}>
        <div className="card" style={{ padding: 20 }}>
          <div className="h2" style={{ marginBottom: 14 }}>Evolución mensual del gasto</div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={evolucionData}>
              <CartesianGrid stroke="var(--border-soft)" vertical={false} />
              <XAxis dataKey="etiqueta" stroke="var(--text-faint)" fontSize={11} />
              <YAxis stroke="var(--text-faint)" fontSize={11} tickFormatter={(v) => `${(v / 1e6).toFixed(0)}M`} />
              <Tooltip
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 12 }}
                formatter={(v) => formatMonto(Number(v))}
              />
              <Line type="monotone" dataKey="gasto" stroke="#e0a339" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div className="h2" style={{ marginBottom: 14 }}>Gasto por área (período)</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={porArea} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid stroke="var(--border-soft)" horizontal={false} />
              <XAxis type="number" stroke="var(--text-faint)" fontSize={11} tickFormatter={(v) => `${(v / 1e6).toFixed(0)}M`} />
              <YAxis type="category" dataKey="nombre" stroke="var(--text-faint)" fontSize={11} width={140} />
              <Tooltip
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 12 }}
                formatter={(v) => formatMonto(Number(v))}
              />
              <Bar dataKey="monto" radius={[0, 3, 3, 0]}>
                {porArea.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card" style={{ padding: 20 }}>
        <div className="h2" style={{ marginBottom: 14 }}>Top 8 proveedores (período)</div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={porProveedor} layout="vertical" margin={{ left: 30 }}>
            <CartesianGrid stroke="var(--border-soft)" horizontal={false} />
            <XAxis type="number" stroke="var(--text-faint)" fontSize={11} tickFormatter={(v) => `${(v / 1e6).toFixed(0)}M`} />
            <YAxis type="category" dataKey="nombre" stroke="var(--text-faint)" fontSize={11} width={170} />
            <Tooltip
              contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 12 }}
              formatter={(v) => formatMonto(Number(v))}
            />
            <Bar dataKey="monto" fill="#5b8fb0" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: React.ReactNode; color?: string }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="faint" style={{ fontSize: 11, marginBottom: 6 }}>{label}</div>
      <div className="mono" style={{ fontSize: 24, fontWeight: 650, color: color || "var(--text)", marginBottom: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 11.5 }} className="faint">{sub}</div>}
    </div>
  );
}
