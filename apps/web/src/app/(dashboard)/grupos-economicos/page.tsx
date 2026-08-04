"use client";

import { useEffect, useState } from "react";
import { api, CompanyItem, ApiError } from "@/lib/api";
import { useGroup } from "@/lib/group-context";

export default function GruposEconomicosPage() {
  const { groups, reloadGroups } = useGroup();
  const [companies, setCompanies] = useState<CompanyItem[] | null>(null);
  const [nuevoGrupo, setNuevoGrupo] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNombre, setEditNombre] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadCompanies() {
    try {
      setCompanies(await api.listCompaniesAdmin());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las empresas.");
    }
  }

  useEffect(() => {
    loadCompanies();
  }, []);

  async function handleCreateGroup() {
    if (!nuevoGrupo.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.createEconomicGroup(nuevoGrupo.trim());
      setNuevoGrupo("");
      await reloadGroups();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el grupo.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveGroup(id: number) {
    setLoading(true);
    setError(null);
    try {
      await api.updateEconomicGroup(id, editNombre);
      setEditingId(null);
      await reloadGroups();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivateGroup(id: number) {
    if (!window.confirm("¿Desactivar este grupo económico? Las empresas asignadas quedan sin grupo.")) return;
    setLoading(true);
    setError(null);
    try {
      await api.deactivateEconomicGroup(id);
      await reloadGroups();
      await loadCompanies();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desactivar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAssignGroup(companyId: number, groupId: string) {
    setLoading(true);
    setError(null);
    try {
      await api.assignCompanyGroup(companyId, groupId ? Number(groupId) : null);
      await Promise.all([loadCompanies(), reloadGroups()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo asignar el grupo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 6 }}>Catálogos</div>
      <h1 className="h1" style={{ marginBottom: 8 }}>Grupos Económicos</h1>
      <p className="muted" style={{ fontSize: 13, marginBottom: 20, maxWidth: 640 }}>
        Agrupá las distintas empresas/razones sociales bajo un mismo grupo económico (ej. Autocity, Grupo Tagle,
        Nuevos Negocios). Desde el selector de la barra lateral podés elegir un grupo activo para que el Dashboard
        y los Reportes muestren solo los datos de las empresas de ese grupo.
      </p>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ padding: 16, marginBottom: 20, display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div className="field" style={{ flex: 1, maxWidth: 300 }}>
          <label>Nuevo grupo económico</label>
          <input value={nuevoGrupo} onChange={(e) => setNuevoGrupo(e.target.value)} placeholder="Ej. Autocity" />
        </div>
        <button className="btn btn-primary" onClick={handleCreateGroup} disabled={loading}>Agregar</button>
      </div>

      <div className="card" style={{ marginBottom: 28 }}>
        <table className="ledger">
          <thead>
            <tr>
              <th>Grupo</th>
              <th style={{ textAlign: "right" }}>Empresas asignadas</th>
              <th style={{ width: 180 }} />
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.id}>
                {editingId === g.id ? (
                  <>
                    <td><input value={editNombre} onChange={(e) => setEditNombre(e.target.value)} style={{ width: "100%" }} /></td>
                    <td className="mono" style={{ textAlign: "right" }}>{g.cantidad_empresas}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => setEditingId(null)}>Cancelar</button>
                        <button className="btn btn-primary" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => handleSaveGroup(g.id)} disabled={loading}>Guardar</button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{g.nombre}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{g.cantidad_empresas}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => { setEditingId(g.id); setEditNombre(g.nombre); }}>Editar</button>
                        <button className="btn btn-danger" style={{ padding: "4px 8px", fontSize: 11.5 }} onClick={() => handleDeactivateGroup(g.id)} disabled={loading}>Desactivar</button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {groups.length === 0 && (
              <tr><td colSpan={3} className="muted" style={{ textAlign: "center", padding: 20 }}>Todavía no creaste ningún grupo económico.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="h2" style={{ marginBottom: 10 }}>Empresas</div>
      <p className="faint" style={{ fontSize: 12, marginBottom: 12 }}>
        Asigná cada empresa (tal como aparece en los CSV de TSDocs) al grupo económico que corresponda.
      </p>
      <div className="card">
        {!companies ? (
          <div className="muted" style={{ padding: 20 }}>Cargando...</div>
        ) : (
          <table className="ledger">
            <thead>
              <tr>
                <th>Empresa</th>
                <th style={{ textAlign: "right" }}>Facturas</th>
                <th>Grupo económico</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => (
                <tr key={c.id}>
                  <td>{c.nombre}</td>
                  <td className="mono" style={{ textAlign: "right" }}>{c.cantidad_facturas}</td>
                  <td>
                    <select
                      value={c.economic_group_id ?? ""}
                      onChange={(e) => handleAssignGroup(c.id, e.target.value)}
                      disabled={loading}
                      style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "6px 8px", color: "var(--text)", minWidth: 200 }}
                    >
                      <option value="">— Sin asignar —</option>
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>{g.nombre}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
