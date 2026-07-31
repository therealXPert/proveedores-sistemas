"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api, DashboardKPIs, RankingItem, ApiError } from "@/lib/api";

const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const COLORS = ["#e0a339", "#5b8fb0", "#4f9d6e", "#d9636f", "#8fa0ac", "#7a5a24"];

function formatMonto(n: number) {
  return n.toLocaleString("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function Pct({ value }: { value: number | null }) {
  if (value === null) return <span className="faint">—</span>;
  const color = value > 0 ? "var(--error)" : "var(--ok)";
  return <span style={{ color }}>{value > 0 ? "+" : ""}{value.toFixed(1)}%</span>;
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [evolucion, setEvolucion] = useState<{ mes: number; gasto: number }[] | null>(null);
  const [porProveedor, setPorProveedor] = useState<RankingItem[] | null>(null);
  const [porArea, setPorArea] = useState<RankingItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const k = await api.dashboard();
        setKpis(k);
        const [evo, prov, area] = await Promise.all([
          api.evolucionMensual(k.anio),
          api.rankingProveedores(k.anio, k.mes),
          api.rankingAreas(k.anio, k.mes),
        ]);
        setEvolucion(evo);
        setPorProveedor(prov.slice(0, 8));
        setPorArea(area);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el dashboard.");
      }
    })();
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!kpis || !evolucion || !porProveedor || !porArea) return <div className="muted">Cargando...</div>;

  const evolucionData = evolucion.map((e) => ({ mes: MESES[e.mes - 1], gasto: e.gasto }));

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>
        Sistemas · {MESES[kpis.mes - 1]} {kpis.anio}
      </div>
      <h1 className="h1" style={{ marginBottom: 24 }}>Dashboard ejecutivo</h1>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
        <KpiCard label="Gasto del mes" value={formatMonto(kpis.gasto_total_mes)} sub={<>vs. mes anterior <Pct value={kpis.variacion_mes_anterior_pct} /></>} />
        <KpiCard label="Acumulado del año" value={formatMonto(kpis.gasto_acumulado_anio)} sub={`Proyección de cierre: ${kpis.proyeccion_cierre_anio ? formatMonto(kpis.proyeccion_cierre_anio) : "—"}`} />
        <KpiCard
          label="% presupuesto consumido"
          value={kpis.porcentaje_consumido_mes !== null ? `${kpis.porcentaje_consumido_mes.toFixed(0)}%` : "—"}
          sub={<>Desvío: <span style={{ color: kpis.desvio_contra_presupuesto_mes > 0 ? "var(--error)" : "var(--ok)" }}>{formatMonto(kpis.desvio_contra_presupuesto_mes)}</span></>}
          color={kpis.porcentaje_consumido_mes && kpis.porcentaje_consumido_mes > 100 ? "var(--error)" : "var(--text)"}
        />
        <KpiCard label="Facturas del mes" value={String(kpis.cantidad_facturas_mes)} sub={`${kpis.cantidad_proveedores_mes} proveedores`} />
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
              <XAxis dataKey="mes" stroke="var(--text-faint)" fontSize={12} />
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
          <div className="h2" style={{ marginBottom: 14 }}>Gasto por área (mes actual)</div>
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
        <div className="h2" style={{ marginBottom: 14 }}>Top 8 proveedores (mes actual)</div>
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
