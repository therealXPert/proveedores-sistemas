"use client";

import { useEffect, useState } from "react";
import { api, BudgetItem, BudgetResumenItem, CatalogItem, ApiError, downloadFile } from "@/lib/api";

function formatMonto(n: number) {
  return n.toLocaleString("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function PresupuestoPage() {
  const [budgets, setBudgets] = useState<BudgetItem[] | null>(null);
  const [resumen, setResumen] = useState<BudgetResumenItem[] | null>(null);
  const [providers, setProviders] = useState<CatalogItem[]>([]);
  const [vista, setVista] = useState<"lineas" | "resumen">("resumen");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editImporte, setEditImporte] = useState("");
  const [editPeriodicidad, setEditPeriodicidad] = useState("Mensual");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const anio = 2026;

  async function load() {
    try {
      const [b, r, p] = await Promise.all([
        api.listBudgets(anio),
        api.budgetResumen(anio),
        api.listProviders(),
      ]);
      setBudgets(b);
      setResumen(r);
      setProviders(p);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el presupuesto.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSaveEdit(id: number) {
    setLoading(true);
    setError(null);
    try {
      await api.updateBudget(id, {
        importe_original: editImporte ? Number(editImporte) : undefined,
        periodicidad_original: editPeriodicidad,
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("¿Eliminar esta línea de presupuesto?")) return;
    setLoading(true);
    setError(null);
    try {
      await api.deleteBudget(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportResumen(formato: "csv" | "xlsx") {
    setError(null);
    try {
      await downloadFile(`/budgets/resumen/export?formato=${formato}&anio=${anio}`, `presupuesto-vs-real.${formato}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo exportar.");
    }
  }

  if (!budgets || !resumen) return <div className="muted">Cargando...</div>;

  const totalPresupuestado = resumen.reduce((acc, r) => acc + r.presupuesto_mensual, 0);
  const totalGastoReal = resumen.reduce((acc, r) => acc + r.gasto_real_promedio_mensual, 0);

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Sistemas · {anio}</div>
      <h1 className="h1" style={{ marginBottom: 20 }}>Presupuesto</h1>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      <div style={{ display: "flex", gap: 24, marginBottom: 24 }}>
        <Metric label="Presupuesto mensual total" value={formatMonto(totalPresupuestado)} />
        <Metric label="Gasto real promedio mensual" value={formatMonto(totalGastoReal)} color={totalGastoReal > totalPresupuestado ? "var(--error)" : "var(--ok)"} />
        <Metric label="Desvío" value={formatMonto(totalGastoReal - totalPresupuestado)} color={totalGastoReal > totalPresupuestado ? "var(--error)" : "var(--ok)"} />
        <Metric label="Proveedores presupuestados" value={String(resumen.length)} />
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <button className={`btn ${vista === "resumen" ? "btn-primary" : ""}`} onClick={() => setVista("resumen")}>
          Resumen por proveedor
        </button>
        <button className={`btn ${vista === "lineas" ? "btn-primary" : ""}`} onClick={() => setVista("lineas")}>
          Líneas de presupuesto ({budgets.length})
        </button>
        {vista === "resumen" && (
          <>
            <div style={{ flex: 1 }} />
            <button className="btn" onClick={() => handleExportResumen("csv")}>Exportar CSV</button>
            <button className="btn" onClick={() => handleExportResumen("xlsx")}>Exportar Excel</button>
          </>
        )}
      </div>

      {vista === "resumen" && (
        <div className="card">
          <table className="ledger">
            <thead>
              <tr>
                <th>Proveedor</th>
                <th style={{ textAlign: "right" }}>Presupuesto mensual</th>
                <th style={{ textAlign: "right" }}>Gasto real promedio/mes</th>
                <th style={{ textAlign: "right" }}>Gasto real total {anio}</th>
                <th style={{ textAlign: "right" }}>Desvío mensual</th>
              </tr>
            </thead>
            <tbody>
              {resumen.map((r) => (
                <tr key={r.provider_id}>
                  <td>{r.provider_nombre}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{formatMonto(r.presupuesto_mensual)}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{formatMonto(r.gasto_real_promedio_mensual)}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{formatMonto(r.gasto_real_total)}</td>
                  <td className="mono" style={{ textAlign: "right", color: r.desvio_mensual > 0 ? "var(--error)" : "var(--ok)" }}>
                    {r.desvio_mensual > 0 ? "+" : ""}{formatMonto(r.desvio_mensual)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {vista === "lineas" && (
        <div className="card">
          <table className="ledger">
            <thead>
              <tr>
                <th>Proveedor</th>
                <th>Área</th>
                <th>Unidad de negocio</th>
                <th>Periodicidad</th>
                <th style={{ textAlign: "right" }}>Importe original</th>
                <th style={{ textAlign: "right" }}>Equivalente mensual</th>
                <th>Comentario</th>
                <th style={{ width: 140 }} />
              </tr>
            </thead>
            <tbody>
              {budgets.map((b) => {
                const isEditing = editingId === b.id;
                return (
                  <tr key={b.id}>
                    <td>{b.provider_nombre ?? "—"}</td>
                    <td className="muted">{b.area_nombre ?? "—"}</td>
                    <td className="muted">{b.business_unit_nombre ?? "—"}</td>
                    <td>
                      {isEditing ? (
                        <select
                          value={editPeriodicidad}
                          onChange={(e) => setEditPeriodicidad(e.target.value)}
                          style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "4px 6px", color: "var(--text)" }}
                        >
                          <option value="Mensual">Mensual</option>
                          <option value="Bimensual">Bimensual</option>
                          <option value="Trimestral">Trimestral</option>
                          <option value="A demanda">A demanda</option>
                        </select>
                      ) : (
                        b.periodicidad_original ?? "—"
                      )}
                    </td>
                    <td className="mono" style={{ textAlign: "right" }}>
                      {isEditing ? (
                        <input
                          type="number"
                          value={editImporte}
                          onChange={(e) => setEditImporte(e.target.value)}
                          style={{ width: 110, textAlign: "right", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "4px 6px", color: "var(--text)" }}
                        />
                      ) : (
                        b.importe_original !== null ? formatMonto(b.importe_original) : "—"
                      )}
                    </td>
                    <td className="mono" style={{ textAlign: "right" }}>
                      {b.importe_mensual_equivalente !== null ? formatMonto(b.importe_mensual_equivalente) : "—"}
                    </td>
                    <td className="faint" style={{ fontSize: 12, maxWidth: 260 }}>{b.comentario ?? "—"}</td>
                    <td>
                      {isEditing ? (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button className="btn" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => setEditingId(null)}>Cancelar</button>
                          <button className="btn btn-primary" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => handleSaveEdit(b.id)} disabled={loading}>Guardar</button>
                        </div>
                      ) : (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn"
                            style={{ padding: "4px 8px", fontSize: 11.5 }}
                            onClick={() => {
                              setEditingId(b.id);
                              setEditImporte(b.importe_original !== null ? String(b.importe_original) : "");
                              setEditPeriodicidad(b.periodicidad_original ?? "Mensual");
                            }}
                          >
                            Editar
                          </button>
                          <button className="btn btn-danger" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => handleDelete(b.id)} disabled={loading}>
                            Eliminar
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div className="faint" style={{ fontSize: 11, marginBottom: 2 }}>{label}</div>
      <div className="mono" style={{ fontSize: 20, fontWeight: 600, color: color || "var(--text)" }}>{value}</div>
    </div>
  );
}
