"use client";

import { useEffect, useState } from "react";
import { api, AuditEvent, ApiError } from "@/lib/api";

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "medium" });
}

const ACCION_LABELS: Record<string, string> = {
  aprobar_carga: "Aprobar carga (lote)",
  rechazar_carga: "Rechazar carga (lote)",
  aprobar_factura: "Aprobar factura",
  rechazar_factura: "Rechazar factura",
  editar_factura_staging: "Editar factura (revisión)",
  eliminar_importacion: "Eliminar importación",
  editar_proveedor: "Editar proveedor",
  agregar_alias_proveedor: "Agregar alias de proveedor",
  eliminar_alias_proveedor: "Eliminar alias de proveedor",
  fusionar_proveedores: "Fusionar proveedores",
  crear_categoria: "Crear categoría",
  editar_categoria: "Editar categoría",
  desactivar_categoria: "Desactivar categoría",
  crear_area: "Crear área",
  editar_area: "Editar área",
  desactivar_area: "Desactivar área",
  agregar_alias_area: "Agregar alias de área",
  eliminar_alias_area: "Eliminar alias de área",
  crear_presupuesto: "Crear presupuesto",
  editar_presupuesto: "Editar presupuesto",
  eliminar_presupuesto: "Eliminar presupuesto",
};

export default function AuditoriaPage() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [acciones, setAcciones] = useState<string[]>([]);
  const [entidades, setEntidades] = useState<string[]>([]);
  const [filtroAccion, setFiltroAccion] = useState("");
  const [filtroEntidad, setFiltroEntidad] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAuditAcciones().then(setAcciones).catch(() => {});
    api.listAuditEntidades().then(setEntidades).catch(() => {});
  }, []);

  async function load() {
    try {
      const data = await api.listAuditEvents({ accion: filtroAccion, entidad: filtroEntidad, limit: 300 });
      setEvents(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la auditoría.");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroAccion, filtroEntidad]);

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Sistemas</div>
      <h1 className="h1" style={{ marginBottom: 20 }}>Auditoría</h1>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <select
          value={filtroAccion}
          onChange={(e) => setFiltroAccion(e.target.value)}
          style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)", minWidth: 220 }}
        >
          <option value="">Todas las acciones</option>
          {acciones.map((a) => (
            <option key={a} value={a}>{ACCION_LABELS[a] ?? a}</option>
          ))}
        </select>
        <select
          value={filtroEntidad}
          onChange={(e) => setFiltroEntidad(e.target.value)}
          style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)", minWidth: 180 }}
        >
          <option value="">Todas las entidades</option>
          {entidades.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
      </div>

      <div className="card">
        {!events ? (
          <div className="muted" style={{ padding: 20 }}>Cargando...</div>
        ) : (
          <table className="ledger">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Acción</th>
                <th>Entidad</th>
                <th>ID</th>
                <th>Motivo</th>
                <th style={{ width: 90 }} />
              </tr>
            </thead>
            <tbody>
              {events.map((e) => {
                const isExpanded = expandedId === e.id;
                const tieneDetalle = e.valor_anterior || e.valor_nuevo;
                return (
                  <>
                    <tr key={e.id}>
                      <td className="mono" style={{ fontSize: 12 }}>{formatFecha(e.fecha)}</td>
                      <td>
                        <div>{e.usuario_nombre ?? "—"}</div>
                        {e.usuario_email && <div className="faint" style={{ fontSize: 11 }}>{e.usuario_email}</div>}
                      </td>
                      <td>{ACCION_LABELS[e.accion] ?? e.accion}</td>
                      <td className="muted">{e.entidad}</td>
                      <td className="mono faint">{e.entidad_id ?? "—"}</td>
                      <td className="muted" style={{ fontSize: 12.5, maxWidth: 220 }}>{e.motivo ?? "—"}</td>
                      <td>
                        {tieneDetalle && (
                          <button className="btn" style={{ padding: "3px 8px", fontSize: 11 }} onClick={() => setExpandedId(isExpanded ? null : e.id)}>
                            {isExpanded ? "Ocultar" : "Detalle"}
                          </button>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${e.id}-detail`}>
                        <td colSpan={7} style={{ background: "var(--surface-raised)", padding: 16 }}>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                            <div>
                              <div className="faint" style={{ fontSize: 11, marginBottom: 6 }}>VALOR ANTERIOR</div>
                              <pre className="mono" style={{ fontSize: 11.5, whiteSpace: "pre-wrap", margin: 0, color: "var(--text-dim)" }}>
                                {e.valor_anterior ? JSON.stringify(e.valor_anterior, null, 2) : "—"}
                              </pre>
                            </div>
                            <div>
                              <div className="faint" style={{ fontSize: 11, marginBottom: 6 }}>VALOR NUEVO</div>
                              <pre className="mono" style={{ fontSize: 11.5, whiteSpace: "pre-wrap", margin: 0, color: "var(--text-dim)" }}>
                                {e.valor_nuevo ? JSON.stringify(e.valor_nuevo, null, 2) : "—"}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
              {events.length === 0 && (
                <tr><td colSpan={7} className="muted" style={{ textAlign: "center", padding: 20 }}>Sin eventos para este filtro.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
