"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ImportBatch, StagingRow, ApiError } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

function formatMonto(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ImportDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const batchId = Number(params.id);

  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [rows, setRows] = useState<StagingRow[] | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function load() {
    try {
      const [b, r] = await Promise.all([api.getImport(batchId), api.previewImport(batchId)]);
      setBatch(b);
      setRows(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la importación.");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  async function handleApprove() {
    setActionLoading(true);
    setError(null);
    try {
      const res = await api.approveImport(batchId);
      setSuccessMsg(
        `Carga aprobada: ${res.filas_aprobadas} facturas cargadas` +
          (res.filas_excluidas_por_error > 0
            ? `, ${res.filas_excluidas_por_error} excluidas por tener errores bloqueantes.`
            : ".")
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo aprobar la carga.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    const motivo = window.prompt("Motivo del rechazo (opcional):") || undefined;
    setActionLoading(true);
    setError(null);
    try {
      await api.rejectImport(batchId, motivo);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo rechazar la carga.");
    } finally {
      setActionLoading(false);
    }
  }

  if (error && !batch) {
    return (
      <div>
        <Link href="/imports" className="muted">
          ← Volver a Importaciones
        </Link>
        <div className="error-banner" style={{ marginTop: 16 }}>
          {error}
        </div>
      </div>
    );
  }

  if (!batch || !rows) {
    return <div className="muted">Cargando...</div>;
  }

  const puedeAprobar = batch.estado === "pendiente_validacion" || batch.estado === "con_errores";

  return (
    <div>
      <Link href="/imports" className="muted" style={{ fontSize: 13, textDecoration: "none" }}>
        ← Volver a Importaciones
      </Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", margin: "16px 0 24px" }}>
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            Importación #{batch.id}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 className="h1">Revisión de carga</h1>
            <StatusBadge estado={batch.estado} />
          </div>
        </div>

        {puedeAprobar && (
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-danger" onClick={handleReject} disabled={actionLoading}>
              Rechazar
            </button>
            <button className="btn btn-primary" onClick={handleApprove} disabled={actionLoading}>
              {actionLoading ? "Procesando..." : "Aprobar carga"}
            </button>
          </div>
        )}
      </div>

      {successMsg && <div className="card" style={{ padding: 14, marginBottom: 16, borderColor: "var(--ok)", color: "var(--ok)" }}>{successMsg}</div>}
      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      {batch.resumen && (
        <div style={{ display: "flex", gap: 24, marginBottom: 24 }}>
          <Metric label="Total filas" value={batch.resumen.total_filas} />
          <Metric label="Válidas" value={batch.resumen.validos} color="var(--ok)" />
          <Metric label="Advertencias" value={batch.resumen.advertencias} color="var(--warn)" />
          <Metric label="Inválidas" value={batch.resumen.invalidos} color="var(--error)" />
          <Metric label="Duplicadas" value={batch.resumen.duplicados} color="var(--info)" />
        </div>
      )}

      <div className="card">
        <table className="ledger">
          <thead>
            <tr>
              <th style={{ width: 40 }} />
              <th>Estado</th>
              <th>Proveedor</th>
              <th>N° Factura</th>
              <th>Fecha</th>
              <th style={{ textAlign: "right" }}>Importe</th>
              <th>Descripción</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const m = row.datos_mapeados;
              const isExpanded = expandedRow === row.id;
              return (
                <>
                  <tr
                    key={row.id}
                    onClick={() => setExpandedRow(isExpanded ? null : row.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td className="faint mono">{row.errores.length > 0 ? row.errores.length : ""}</td>
                    <td>
                      <StatusBadge estado={row.estado_fila} />
                    </td>
                    <td>{String(m.proveedor_razon_social ?? "—")}</td>
                    <td className="mono">{String(m.numero_factura ?? "—")}</td>
                    <td className="mono">
                      {m.fecha_emision ? new Date(String(m.fecha_emision)).toLocaleDateString("es-AR") : "—"}
                    </td>
                    <td className="mono" style={{ textAlign: "right" }}>
                      {formatMonto(m.importe_total)} {String(m.moneda ?? "")}
                    </td>
                    <td className="muted" style={{ maxWidth: 320 }}>
                      {String(m.descripcion ?? "—")}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${row.id}-detail`}>
                      <td />
                      <td colSpan={6} style={{ background: "var(--surface-raised)", padding: 16 }}>
                        {row.errores.length > 0 && (
                          <div style={{ marginBottom: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                            {row.errores.map((e, i) => (
                              <div key={i} style={{ fontSize: 12.5 }}>
                                <StatusBadge estado={e.severidad === "bloqueante" ? "error" : "advertencia"} />{" "}
                                <span className="muted">{e.mensaje}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="faint" style={{ fontSize: 12 }}>
                          Descripción completa: <span className="muted">{String(m.descripcion ?? "—")}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div>
      <div className="faint" style={{ fontSize: 11, marginBottom: 2 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 20, fontWeight: 600, color: color || "var(--text)" }}>
        {value}
      </div>
    </div>
  );
}
