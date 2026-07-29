"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ImportBatch, StagingRow, StagingRowUpdate, CatalogItem, ApiError } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import EditStagingRowForm from "@/components/EditStagingRowForm";

function formatMonto(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

type Catalogs = {
  providers: CatalogItem[];
  areas: CatalogItem[];
  categories: CatalogItem[];
  costCenters: CatalogItem[];
  businessUnits: CatalogItem[];
  companies: CatalogItem[];
  branches: CatalogItem[];
};

const EMPTY_CATALOGS: Catalogs = {
  providers: [],
  areas: [],
  categories: [],
  costCenters: [],
  businessUnits: [],
  companies: [],
  branches: [],
};

function nombreCatalogo(items: CatalogItem[], id: unknown): string {
  if (id === null || id === undefined) return "—";
  const found = items.find((i) => i.id === Number(id));
  return found ? found.nombre : "—";
}

export default function ImportDetailPage() {
  const params = useParams<{ id: string }>();
  const batchId = Number(params.id);

  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [rows, setRows] = useState<StagingRow[] | null>(null);
  const [catalogs, setCatalogs] = useState<Catalogs>(EMPTY_CATALOGS);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [rowActionLoading, setRowActionLoading] = useState<number | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [b, r] = await Promise.all([api.getImport(batchId), api.previewImport(batchId)]);
      setBatch(b);
      setRows(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la importación.");
    }
  }

  async function loadCatalogs() {
    try {
      const [providers, areas, categories, costCenters, businessUnits, companies, branches] = await Promise.all([
        api.listProviders(),
        api.listAreas(),
        api.listCategories(),
        api.listCostCenters(),
        api.listBusinessUnits(),
        api.listCompanies(),
        api.listBranches(),
      ]);
      setCatalogs({ providers, areas, categories, costCenters, businessUnits, companies, branches });
    } catch {
      // los catalogos son para el formulario de edicion; si fallan, igual se puede ver/aprobar/rechazar
    }
  }

  useEffect(() => {
    load();
    loadCatalogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  async function handleApproveRow(stagingId: number) {
    setRowActionLoading(stagingId);
    setError(null);
    try {
      await api.approveRow(stagingId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo aprobar esta factura.");
    } finally {
      setRowActionLoading(null);
    }
  }

  async function handleRejectRow(stagingId: number) {
    const motivo = window.prompt("Motivo del rechazo (opcional):") ?? undefined;
    setRowActionLoading(stagingId);
    setError(null);
    try {
      await api.rejectRow(stagingId, motivo);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo rechazar esta factura.");
    } finally {
      setRowActionLoading(null);
    }
  }

  async function handleSaveEdit(stagingId: number, updates: StagingRowUpdate) {
    setRowActionLoading(stagingId);
    setError(null);
    try {
      await api.updateRow(stagingId, updates);
      setEditingRow(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron guardar los cambios.");
    } finally {
      setRowActionLoading(null);
    }
  }

  async function handleApprovePendientes() {
    setBulkLoading(true);
    setError(null);
    try {
      await api.approveImport(batchId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron aprobar las facturas pendientes.");
    } finally {
      setBulkLoading(false);
    }
  }

  async function handleRejectPendientes() {
    const motivo = window.prompt("Motivo del rechazo para todas las pendientes (opcional):") ?? undefined;
    setBulkLoading(true);
    setError(null);
    try {
      await api.rejectImport(batchId, motivo);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron rechazar las facturas pendientes.");
    } finally {
      setBulkLoading(false);
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

  const pendientes = rows.filter((r) => r.resultado === "pendiente");
  const hayPendientes = pendientes.length > 0;

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

        {hayPendientes && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
            <div className="faint" style={{ fontSize: 11 }}>
              {pendientes.length} factura{pendientes.length !== 1 ? "s" : ""} pendiente{pendientes.length !== 1 ? "s" : ""}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-danger" onClick={handleRejectPendientes} disabled={bulkLoading}>
                Rechazar pendientes
              </button>
              <button className="btn btn-primary" onClick={handleApprovePendientes} disabled={bulkLoading}>
                {bulkLoading ? "Procesando..." : "Aprobar pendientes"}
              </button>
            </div>
          </div>
        )}
      </div>

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
              <th>Validación</th>
              <th>Decisión</th>
              <th>Proveedor</th>
              <th>N° Factura</th>
              <th>Fecha</th>
              <th style={{ textAlign: "right" }}>Importe</th>
              <th>Descripción</th>
              <th style={{ width: 230 }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const m = row.datos_mapeados;
              const isExpanded = expandedRow === row.id;
              const isEditing = editingRow === row.id;
              const isLoadingThis = rowActionLoading === row.id;
              const yaDecidida = row.resultado !== "pendiente";

              return (
                <>
                  <tr key={row.id} style={{ opacity: yaDecidida ? 0.65 : 1 }}>
                    <td>
                      <StatusBadge estado={row.estado_fila} />
                    </td>
                    <td>
                      <StatusBadge estado={row.resultado} />
                    </td>
                    <td>{nombreCatalogo(catalogs.providers, m.provider_id) !== "—" ? nombreCatalogo(catalogs.providers, m.provider_id) : String(m.proveedor_razon_social ?? "—")}</td>
                    <td className="mono">{String(m.numero_factura ?? "—")}</td>
                    <td className="mono">
                      {m.fecha_emision ? new Date(String(m.fecha_emision)).toLocaleDateString("es-AR") : "—"}
                    </td>
                    <td className="mono" style={{ textAlign: "right" }}>
                      {formatMonto(m.importe_total)} {String(m.moneda ?? "")}
                    </td>
                    <td className="muted" style={{ maxWidth: 260 }}>
                      <button
                        onClick={() => {
                          setExpandedRow(isExpanded ? null : row.id);
                          if (isEditing) setEditingRow(null);
                        }}
                        style={{
                          background: "none",
                          border: "none",
                          color: "inherit",
                          textAlign: "left",
                          cursor: "pointer",
                          padding: 0,
                          font: "inherit",
                        }}
                      >
                        {String(m.descripcion ?? "—")}
                      </button>
                    </td>
                    <td>
                      {!yaDecidida && !isEditing && (
                        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                          <button
                            className="btn"
                            style={{ padding: "4px 8px", fontSize: 11.5 }}
                            onClick={() => {
                              setEditingRow(row.id);
                              setExpandedRow(row.id);
                            }}
                            disabled={isLoadingThis}
                          >
                            Editar
                          </button>
                          <button
                            className="btn btn-danger"
                            style={{ padding: "4px 8px", fontSize: 11.5 }}
                            onClick={() => handleRejectRow(row.id)}
                            disabled={isLoadingThis}
                          >
                            Rechazar
                          </button>
                          <button
                            className="btn btn-primary"
                            style={{ padding: "4px 8px", fontSize: 11.5 }}
                            onClick={() => handleApproveRow(row.id)}
                            disabled={isLoadingThis}
                          >
                            {isLoadingThis ? "..." : "Aprobar"}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${row.id}-detail`}>
                      <td colSpan={8} style={{ background: "var(--surface-raised)", padding: 16 }}>
                        {isEditing ? (
                          <EditStagingRowForm
                            row={row}
                            catalogs={catalogs}
                            saving={isLoadingThis}
                            onCancel={() => setEditingRow(null)}
                            onSave={(updates) => handleSaveEdit(row.id, updates)}
                          />
                        ) : (
                          <>
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
                            <div className="faint" style={{ fontSize: 12, marginBottom: 4 }}>
                              Descripción completa: <span className="muted">{String(m.descripcion ?? "—")}</span>
                            </div>
                            <div className="faint" style={{ fontSize: 12, marginBottom: 4 }}>
                              Área: <span className="muted">{nombreCatalogo(catalogs.areas, m.area_id)}</span>
                              {"  ·  "}Categoría: <span className="muted">{nombreCatalogo(catalogs.categories, m.category_id)}</span>
                              {"  ·  "}Centro de costo: <span className="muted">{nombreCatalogo(catalogs.costCenters, m.cost_center_id)}</span>
                            </div>
                            <div className="faint" style={{ fontSize: 12, marginBottom: row.motivo_rechazo ? 6 : 0 }}>
                              Unidad de negocio: <span className="muted">{nombreCatalogo(catalogs.businessUnits, m.business_unit_id)}</span>
                              {"  ·  "}Empresa: <span className="muted">{nombreCatalogo(catalogs.companies, m.company_id)}</span>
                              {"  ·  "}Sucursal: <span className="muted">{nombreCatalogo(catalogs.branches, m.branch_id)}</span>
                            </div>
                            {row.motivo_rechazo && (
                              <div className="faint" style={{ fontSize: 12 }}>
                                Motivo del rechazo: <span className="muted">{row.motivo_rechazo}</span>
                              </div>
                            )}
                          </>
                        )}
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
