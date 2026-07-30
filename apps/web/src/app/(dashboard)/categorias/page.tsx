"use client";

import { useEffect, useState } from "react";
import { api, Category, ApiError } from "@/lib/api";

export default function CategoriasPage() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNombre, setEditNombre] = useState("");
  const [editCodigo, setEditCodigo] = useState("");
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [nuevoCodigo, setNuevoCodigo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setCategories(await api.listCategoriesAdmin());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las categorías.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate() {
    if (!nuevoNombre.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.createCategory({ nombre: nuevoNombre.trim(), codigo_erp: nuevoCodigo.trim() || undefined });
      setNuevoNombre("");
      setNuevoCodigo("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la categoría.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(id: number) {
    setLoading(true);
    setError(null);
    try {
      await api.updateCategory(id, { nombre: editNombre, codigo_erp: editCodigo || undefined });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivate(id: number) {
    if (!window.confirm("¿Desactivar esta categoría? Ya no va a aparecer para elegir en nuevas facturas, pero las existentes no se modifican.")) return;
    setLoading(true);
    setError(null);
    try {
      await api.deactivateCategory(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desactivar.");
    } finally {
      setLoading(false);
    }
  }

  if (!categories) return <div className="muted">Cargando...</div>;

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Catálogos</div>
      <h1 className="h1" style={{ marginBottom: 20 }}>Categorías de gasto</h1>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ padding: 16, marginBottom: 20, display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div className="field" style={{ flex: 1, maxWidth: 280 }}>
          <label>Nueva categoría</label>
          <input value={nuevoNombre} onChange={(e) => setNuevoNombre(e.target.value)} placeholder="Nombre" />
        </div>
        <div className="field" style={{ width: 140 }}>
          <label>Código ERP</label>
          <input value={nuevoCodigo} onChange={(e) => setNuevoCodigo(e.target.value)} placeholder="Ej. ST09" />
        </div>
        <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>Agregar</button>
      </div>

      <div className="card">
        <table className="ledger">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Código ERP</th>
              <th>Categoría padre</th>
              <th style={{ width: 160 }} />
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr key={c.id}>
                {editingId === c.id ? (
                  <>
                    <td><input value={editNombre} onChange={(e) => setEditNombre(e.target.value)} style={{ width: "100%" }} /></td>
                    <td><input value={editCodigo} onChange={(e) => setEditCodigo(e.target.value)} style={{ width: 100 }} /></td>
                    <td className="muted">{c.categoria_padre_nombre ?? "—"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => setEditingId(null)}>Cancelar</button>
                        <button className="btn btn-primary" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => handleSave(c.id)} disabled={loading}>Guardar</button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{c.nombre}</td>
                    <td className="mono">{c.codigo_erp ?? "—"}</td>
                    <td className="muted">{c.categoria_padre_nombre ?? "—"}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          className="btn"
                          style={{ padding: "4px 8px", fontSize: 11.5 }}
                          onClick={() => { setEditingId(c.id); setEditNombre(c.nombre); setEditCodigo(c.codigo_erp ?? ""); }}
                        >
                          Editar
                        </button>
                        <button className="btn btn-danger" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => handleDeactivate(c.id)} disabled={loading}>
                          Desactivar
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
