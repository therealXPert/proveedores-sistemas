"use client";

import { useEffect, useState } from "react";
import { api, Provider, ProviderUpdate, CatalogItem, ApiError } from "@/lib/api";

export default function ProveedoresPage() {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [categories, setCategories] = useState<CatalogItem[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<ProviderUpdate>({});
  const [nuevoAlias, setNuevoAlias] = useState("");
  const [mergeTargetId, setMergeTargetId] = useState<Record<number, string>>({});
  const [loadingAction, setLoadingAction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtro, setFiltro] = useState("");

  async function load() {
    try {
      const [p, c] = await Promise.all([api.listProvidersAdmin(), api.listCategories()]);
      setProviders(p);
      setCategories(c);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los proveedores.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openEdit(p: Provider) {
    setExpandedId(p.id);
    setEditForm({
      nombre_normalizado: p.nombre_normalizado,
      razon_social: p.razon_social ?? "",
      cuit: p.cuit ?? "",
      categoria_principal_id: p.categoria_principal_id ?? undefined,
      moneda_habitual: p.moneda_habitual ?? "ARS",
      condiciones_comerciales: p.condiciones_comerciales ?? "",
      observaciones: p.observaciones ?? "",
    });
    setNuevoAlias("");
  }

  async function handleSave(id: number) {
    setLoadingAction(true);
    setError(null);
    try {
      await api.updateProvider(id, editForm);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el proveedor.");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleAddAlias(id: number) {
    if (!nuevoAlias.trim()) return;
    setLoadingAction(true);
    setError(null);
    try {
      await api.addProviderAlias(id, nuevoAlias.trim());
      setNuevoAlias("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo agregar el alias.");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleDeleteAlias(aliasId: number) {
    setLoadingAction(true);
    setError(null);
    try {
      await api.deleteProviderAlias(aliasId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar el alias.");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleMerge(targetId: number) {
    const otherIdStr = mergeTargetId[targetId];
    const otherId = Number(otherIdStr);
    if (!otherId) return;

    const target = providers?.find((p) => p.id === targetId);
    const other = providers?.find((p) => p.id === otherId);
    const confirmado = window.confirm(
      `¿Fusionar "${other?.nombre_normalizado}" dentro de "${target?.nombre_normalizado}"?\n\n` +
        `Todas las facturas, alias y presupuestos de "${other?.nombre_normalizado}" pasan a "${target?.nombre_normalizado}", ` +
        `y "${other?.nombre_normalizado}" se elimina (queda como alias del que sobrevive). Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;

    setLoadingAction(true);
    setError(null);
    try {
      const resultado = await api.mergeProviders(targetId, otherId);
      window.alert(
        `Fusión completada: ${resultado.facturas_reasignadas} facturas, ${resultado.alias_reasignados} alias ` +
          `y ${resultado.presupuestos_reasignados} presupuestos reasignados.`
      );
      setMergeTargetId((prev) => ({ ...prev, [targetId]: "" }));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo fusionar los proveedores.");
    } finally {
      setLoadingAction(false);
    }
  }

  if (!providers) {
    return <div className="muted">Cargando...</div>;
  }

  const filtrados = providers.filter((p) => {
    const texto = filtro.toLowerCase();
    return (
      p.nombre_normalizado.toLowerCase().includes(texto) ||
      (p.razon_social ?? "").toLowerCase().includes(texto) ||
      (p.cuit ?? "").includes(texto) ||
      p.aliases.some((a) => a.alias_texto.toLowerCase().includes(texto))
    );
  });

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>
        Catálogos
      </div>
      <h1 className="h1" style={{ marginBottom: 20 }}>
        Proveedores
      </h1>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      <input
        placeholder="Buscar por nombre, razón social, CUIT o alias..."
        value={filtro}
        onChange={(e) => setFiltro(e.target.value)}
        style={{
          width: "100%",
          maxWidth: 420,
          marginBottom: 16,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          padding: "9px 11px",
          color: "var(--text)",
        }}
      />

      <div className="card">
        <table className="ledger">
          <thead>
            <tr>
              <th>Nombre normalizado</th>
              <th>Razón social</th>
              <th>CUIT</th>
              <th>Categoría</th>
              <th style={{ textAlign: "right" }}>Facturas</th>
              <th style={{ textAlign: "right" }}>Alias</th>
              <th style={{ width: 90 }} />
            </tr>
          </thead>
          <tbody>
            {filtrados.map((p) => {
              const isExpanded = expandedId === p.id;
              return (
                <>
                  <tr key={p.id}>
                    <td>{p.nombre_normalizado}</td>
                    <td className="muted">{p.razon_social ?? "—"}</td>
                    <td className="mono">{p.cuit ?? "—"}</td>
                    <td className="muted">{p.categoria_principal_nombre ?? "—"}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{p.cantidad_facturas}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{p.aliases.length}</td>
                    <td>
                      <button
                        className="btn"
                        style={{ padding: "4px 10px", fontSize: 11.5 }}
                        onClick={() => (isExpanded ? setExpandedId(null) : openEdit(p))}
                      >
                        {isExpanded ? "Cerrar" : "Editar"}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${p.id}-edit`}>
                      <td colSpan={7} style={{ background: "var(--surface-raised)", padding: 20 }}>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
                          <div className="field">
                            <label>Nombre normalizado</label>
                            <input
                              value={editForm.nombre_normalizado ?? ""}
                              onChange={(e) => setEditForm({ ...editForm, nombre_normalizado: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Razón social</label>
                            <input
                              value={editForm.razon_social ?? ""}
                              onChange={(e) => setEditForm({ ...editForm, razon_social: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>CUIT</label>
                            <input
                              value={editForm.cuit ?? ""}
                              onChange={(e) => setEditForm({ ...editForm, cuit: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Categoría principal</label>
                            <select
                              value={editForm.categoria_principal_id ?? ""}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  categoria_principal_id: e.target.value ? Number(e.target.value) : undefined,
                                })
                              }
                              style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "9px 11px", color: "var(--text)" }}
                            >
                              <option value="">— Sin definir —</option>
                              {categories.map((c) => (
                                <option key={c.id} value={c.id}>{c.nombre}</option>
                              ))}
                            </select>
                          </div>
                          <div className="field">
                            <label>Moneda habitual</label>
                            <input
                              value={editForm.moneda_habitual ?? ""}
                              onChange={(e) => setEditForm({ ...editForm, moneda_habitual: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Condiciones comerciales</label>
                            <input
                              value={editForm.condiciones_comerciales ?? ""}
                              onChange={(e) => setEditForm({ ...editForm, condiciones_comerciales: e.target.value })}
                            />
                          </div>
                        </div>
                        <div className="field" style={{ marginBottom: 16 }}>
                          <label>Observaciones</label>
                          <input
                            value={editForm.observaciones ?? ""}
                            onChange={(e) => setEditForm({ ...editForm, observaciones: e.target.value })}
                          />
                        </div>
                        <button className="btn btn-primary" onClick={() => handleSave(p.id)} disabled={loadingAction} style={{ marginBottom: 20 }}>
                          Guardar cambios
                        </button>

                        <div className="divider" />

                        <div style={{ marginBottom: 20 }}>
                          <div className="h2" style={{ marginBottom: 10 }}>Alias ({p.aliases.length})</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                            {p.aliases.map((a) => (
                              <span
                                key={a.id}
                                className="mono"
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 6,
                                  background: "var(--surface)",
                                  border: "1px solid var(--border)",
                                  borderRadius: "var(--radius)",
                                  padding: "3px 8px",
                                  fontSize: 12,
                                }}
                              >
                                {a.alias_texto}
                                <button
                                  onClick={() => handleDeleteAlias(a.id)}
                                  disabled={loadingAction}
                                  style={{ background: "none", border: "none", color: "var(--error)", cursor: "pointer", padding: 0, fontSize: 13, lineHeight: 1 }}
                                  title="Eliminar alias"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <input
                              placeholder="Nuevo alias (ej. como aparece en un CSV)"
                              value={nuevoAlias}
                              onChange={(e) => setNuevoAlias(e.target.value)}
                              style={{ flex: 1, maxWidth: 320, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)" }}
                            />
                            <button className="btn" onClick={() => handleAddAlias(p.id)} disabled={loadingAction}>
                              Agregar alias
                            </button>
                          </div>
                        </div>

                        <div className="divider" />

                        <div>
                          <div className="h2" style={{ marginBottom: 6 }}>Fusionar con otro proveedor</div>
                          <div className="faint" style={{ fontSize: 12, marginBottom: 10 }}>
                            El proveedor elegido se elimina; sus facturas, alias y presupuestos pasan a "{p.nombre_normalizado}".
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <select
                              value={mergeTargetId[p.id] ?? ""}
                              onChange={(e) => setMergeTargetId({ ...mergeTargetId, [p.id]: e.target.value })}
                              style={{ flex: 1, maxWidth: 320, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)" }}
                            >
                              <option value="">— Elegir proveedor a fusionar —</option>
                              {providers.filter((o) => o.id !== p.id).map((o) => (
                                <option key={o.id} value={o.id}>
                                  {o.nombre_normalizado} ({o.cantidad_facturas} facturas)
                                </option>
                              ))}
                            </select>
                            <button className="btn btn-danger" onClick={() => handleMerge(p.id)} disabled={loadingAction || !mergeTargetId[p.id]}>
                              Fusionar
                            </button>
                          </div>
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
