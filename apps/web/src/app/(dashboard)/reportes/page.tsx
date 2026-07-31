"use client";

import { useEffect, useState } from "react";
import { api, RankingItem, InvoiceItem, CatalogItem, ApiError } from "@/lib/api";

function formatMonto(n: number) {
  return n.toLocaleString("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

type Vista = "concentracion" | "por-area" | "facturas";

export default function ReportesPage() {
  const [vista, setVista] = useState<Vista>("concentracion");
  const [anio] = useState(2026);

  const [proveedores, setProveedores] = useState<RankingItem[] | null>(null);
  const [areas, setAreas] = useState<RankingItem[] | null>(null);
  const [invoices, setInvoices] = useState<InvoiceItem[] | null>(null);
  const [providersCatalog, setProvidersCatalog] = useState<CatalogItem[]>([]);

  const [filtroMes, setFiltroMes] = useState("");
  const [filtroProveedor, setFiltroProveedor] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProviders().then(setProvidersCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    setError(null);
    if (vista === "concentracion") {
      api.rankingProveedores(anio).then(setProveedores).catch((e) => setError(e instanceof ApiError ? e.message : "Error"));
    } else if (vista === "por-area") {
      api.rankingAreas(anio).then(setAreas).catch((e) => setError(e instanceof ApiError ? e.message : "Error"));
    } else {
      loadInvoices();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vista]);

  async function loadInvoices() {
    try {
      const data = await api.listInvoices({
        anio,
        mes: filtroMes ? Number(filtroMes) : undefined,
        provider_id: filtroProveedor ? Number(filtroProveedor) : undefined,
        limit: 200,
      });
      setInvoices(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las facturas.");
    }
  }

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Sistemas · {anio}</div>
      <h1 className="h1" style={{ marginBottom: 20 }}>Reportes</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button className={`btn ${vista === "concentracion" ? "btn-primary" : ""}`} onClick={() => setVista("concentracion")}>
          Concentración de proveedores
        </button>
        <button className={`btn ${vista === "por-area" ? "btn-primary" : ""}`} onClick={() => setVista("por-area")}>
          Evolución por área
        </button>
        <button className={`btn ${vista === "facturas" ? "btn-primary" : ""}`} onClick={() => setVista("facturas")}>
          Detalle de facturas
        </button>
      </div>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {vista === "concentracion" && (
        <div className="card">
          {!proveedores ? (
            <div className="muted" style={{ padding: 20 }}>Cargando...</div>
          ) : (
            <table className="ledger">
              <thead>
                <tr>
                  <th style={{ width: 40 }}>#</th>
                  <th>Proveedor</th>
                  <th style={{ textAlign: "right" }}>Gasto</th>
                  <th style={{ textAlign: "right" }}>Participación</th>
                  <th style={{ textAlign: "right" }}>Acumulado</th>
                </tr>
              </thead>
              <tbody>
                {proveedores.map((p, i) => (
                  <tr key={p.provider_id}>
                    <td className="faint mono">{i + 1}</td>
                    <td>{p.nombre}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{formatMonto(p.monto)}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{p.participacion_pct.toFixed(1)}%</td>
                    <td className="mono" style={{ textAlign: "right", color: p.acumulado_pct <= 80 ? "var(--warn)" : "var(--text-faint)" }}>
                      {p.acumulado_pct.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {vista === "por-area" && (
        <div className="card">
          {!areas ? (
            <div className="muted" style={{ padding: 20 }}>Cargando...</div>
          ) : (
            <table className="ledger">
              <thead>
                <tr>
                  <th>Área</th>
                  <th style={{ textAlign: "right" }}>Gasto</th>
                  <th style={{ textAlign: "right" }}>Participación</th>
                </tr>
              </thead>
              <tbody>
                {areas.map((a) => (
                  <tr key={a.area_id}>
                    <td>{a.nombre}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{formatMonto(a.monto)}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{a.participacion_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {vista === "facturas" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <select
              value={filtroMes}
              onChange={(e) => setFiltroMes(e.target.value)}
              style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)" }}
            >
              <option value="">Todos los meses</option>
              {["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"].map((m, i) => (
                <option key={i} value={i + 1}>{m}</option>
              ))}
            </select>
            <select
              value={filtroProveedor}
              onChange={(e) => setFiltroProveedor(e.target.value)}
              style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)", minWidth: 220 }}
            >
              <option value="">Todos los proveedores</option>
              {providersCatalog.map((p) => (
                <option key={p.id} value={p.id}>{p.nombre}</option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={loadInvoices}>Filtrar</button>
          </div>

          <div className="card">
            {!invoices ? (
              <div className="muted" style={{ padding: 20 }}>Cargando...</div>
            ) : (
              <table className="ledger">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Proveedor</th>
                    <th>N° Factura</th>
                    <th>Área</th>
                    <th>Categoría</th>
                    <th style={{ textAlign: "right" }}>Importe</th>
                    <th>Descripción</th>
                    <th>Aprobó</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id}>
                      <td className="mono">{new Date(inv.fecha_emision).toLocaleDateString("es-AR")}</td>
                      <td className="faint" style={{ fontSize: 11.5 }}>{inv.tipo_documento}</td>
                      <td>{inv.provider_nombre ?? "—"}</td>
                      <td className="mono">{inv.numero_factura ?? "—"}</td>
                      <td className="muted">{inv.area_nombre ?? "—"}</td>
                      <td className="muted">{inv.category_nombre ?? "—"}</td>
                      <td className="mono" style={{ textAlign: "right" }}>{formatMonto(inv.importe_total)}</td>
                      <td className="muted" style={{ maxWidth: 220 }}>{inv.descripcion ?? "—"}</td>
                      <td className="faint" style={{ fontSize: 11.5 }}>{inv.usuario_aprobador_nombre ?? "—"}</td>
                    </tr>
                  ))}
                  {invoices.length === 0 && (
                    <tr><td colSpan={9} className="muted" style={{ textAlign: "center", padding: 20 }}>Sin resultados para este filtro.</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
