"use client";

import { useEffect, useState } from "react";
import { api, AreaAdmin, ApiError } from "@/lib/api";

export default function AreasPage() {
  const [areas, setAreas] = useState<AreaAdmin[] | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editNombre, setEditNombre] = useState("");
  const [nuevoAlias, setNuevoAlias] = useState("");
  const [nuevaArea, setNuevaArea] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setAreas(await api.listAreasAdmin());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las áreas.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate() {
    if (!nuevaArea.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.createArea(nuevaArea.trim());
      setNuevaArea("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el área.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveNombre(id: number) {
    setLoading(true);
    setError(null);
    try {
      await api.updateArea(id, editNombre);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAddAlias(id: number) {
    if (!nuevoAlias.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.addAreaAlias(id, nuevoAlias.trim());
      setNuevoAlias("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo agregar el alias.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteAlias(aliasId: number) {
    setLoading(true);
    setError(null);
    try {
      await api.deleteAreaAlias(aliasId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar el alias.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivate(id: number) {
    if (!window.confirm("¿Desactivar esta área?")) return;
    setLoading(true);
    setError(null);
    try {
      await api.deactivateArea(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desactivar.");
    } finally {
      setLoading(false);
    }
  }

  if (!areas) return <div className="muted">Cargando...</div>;

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Catálogos</div>
      <h1 className="h1" style={{ marginBottom: 20 }}>Áreas</h1>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ padding: 16, marginBottom: 20, display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div className="field" style={{ flex: 1, maxWidth: 320 }}>
          <label>Nueva área</label>
          <input value={nuevaArea} onChange={(e) => setNuevaArea(e.target.value)} placeholder="Nombre del área" />
        </div>
        <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>Agregar</button>
      </div>

      <div className="card">
        <table className="ledger">
          <thead>
            <tr>
              <th>Nombre normalizado</th>
              <th style={{ textAlign: "right" }}>Facturas</th>
              <th style={{ textAlign: "right" }}>Alias</th>
              <th style={{ width: 100 }} />
            </tr>
          </thead>
          <tbody>
            {areas.map((a) => {
              const isExpanded = expandedId === a.id;
              return (
                <>
                  <tr key={a.id}>
                    <td>{a.nombre_normalizado}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{a.cantidad_facturas}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{a.aliases.length}</td>
                    <td>
                      <button
                        className="btn"
                        style={{ padding: "4px 10px", fontSize: 11.5 }}
                        onClick={() => {
                          if (isExpanded) { setExpandedId(null); return; }
                          setExpandedId(a.id);
                          setEditNombre(a.nombre_normalizado);
                          setNuevoAlias("");
                        }}
                      >
                        {isExpanded ? "Cerrar" : "Editar"}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${a.id}-edit`}>
                      <td colSpan={4} style={{ background: "var(--surface-raised)", padding: 18 }}>
                        <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "flex-end" }}>
                          <div className="field" style={{ flex: 1, maxWidth: 320 }}>
                            <label>Nombre normalizado</label>
                            <input value={editNombre} onChange={(e) => setEditNombre(e.target.value)} />
                          </div>
                          <button className="btn btn-primary" onClick={() => handleSaveNombre(a.id)} disabled={loading}>Guardar</button>
                          <button className="btn btn-danger" onClick={() => handleDeactivate(a.id)} disabled={loading}>Desactivar área</button>
                        </div>

                        <div className="h2" style={{ marginBottom: 10 }}>Alias ({a.aliases.length})</div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                          {a.aliases.map((al) => (
                            <span
                              key={al.id}
                              className="mono"
                              style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "3px 8px", fontSize: 12 }}
                            >
                              {al.alias_texto}
                              <button onClick={() => handleDeleteAlias(al.id)} disabled={loading} style={{ background: "none", border: "none", color: "var(--error)", cursor: "pointer", padding: 0, fontSize: 13 }} title="Eliminar alias">×</button>
                            </span>
                          ))}
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                          <input
                            placeholder="Nuevo alias"
                            value={nuevoAlias}
                            onChange={(e) => setNuevoAlias(e.target.value)}
                            style={{ flex: 1, maxWidth: 320, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px 11px", color: "var(--text)" }}
                          />
                          <button className="btn" onClick={() => handleAddAlias(a.id)} disabled={loading}>Agregar alias</button>
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
