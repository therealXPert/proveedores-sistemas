"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, ImportBatch, ApiError } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { useGroup } from "@/lib/group-context";

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

export default function ImportsPage() {
  const { activeGroupId, groups } = useGroup();
  const [batches, setBatches] = useState<ImportBatch[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadBatches() {
    try {
      const data = await api.listImports(activeGroupId);
      setBatches(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el listado.");
    }
  }

  useEffect(() => {
    loadBatches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGroupId]);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      await api.uploadImport(file);
      await loadBatches();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo subir el archivo.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete(batch: ImportBatch) {
    const mensaje =
      batch.estado === "aprobado"
        ? `Esta importación ya está APROBADA: sus datos ya están imputados en los reportes.\n\n` +
          `Eliminarla también va a borrar todas las facturas aprobadas que generó (${batch.resumen?.validos ?? "?"} aprox.). ` +
          `Esta acción no se puede deshacer.\n\n¿Confirmás que querés eliminarla igual?`
        : `¿Eliminar esta importación (#${batch.id})? Esta acción no se puede deshacer.`;

    if (!window.confirm(mensaje)) return;

    setDeletingId(batch.id);
    setError(null);
    try {
      const resultado = await api.deleteImport(batch.id);
      if (resultado.facturas_eliminadas > 0) {
        window.alert(`Importación eliminada junto con ${resultado.facturas_eliminadas} facturas aprobadas.`);
      }
      await loadBatches();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar la importación.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            Facturas · {activeGroupId ? groups.find((g) => g.id === activeGroupId)?.nombre : "Todos los grupos"}
          </div>
          <h1 className="h1">Importaciones</h1>
        </div>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileChange}
            style={{ display: "none" }}
            id="file-upload"
          />
          <label htmlFor="file-upload" className="btn btn-primary" style={{ cursor: uploading ? "not-allowed" : "pointer" }}>
            {uploading ? "Subiendo y validando..." : "Subir archivo CSV / Excel"}
          </label>
        </div>
      </div>

      {error && <div className="error-banner" style={{ marginBottom: 20 }}>{error}</div>}

      <div className="card">
        <table className="ledger">
          <thead>
            <tr>
              <th style={{ width: 56 }}>#</th>
              <th>Fecha de carga</th>
              <th>Estado</th>
              <th>Filas</th>
              <th>Válidas</th>
              <th>Advertencias</th>
              <th>Inválidas</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {batches === null && (
              <tr>
                <td colSpan={8} className="muted" style={{ padding: 20, textAlign: "center" }}>
                  Cargando...
                </td>
              </tr>
            )}
            {batches?.length === 0 && (
              <tr>
                <td colSpan={8} className="muted" style={{ padding: 20, textAlign: "center" }}>
                  Todavía no se subió ningún archivo. Usá el botón de arriba para empezar.
                </td>
              </tr>
            )}
            {batches?.map((b) => (
              <tr key={b.id}>
                <td className="mono faint">{b.id}</td>
                <td className="mono">{formatFecha(b.created_at)}</td>
                <td>
                  <StatusBadge estado={b.estado} />
                </td>
                <td className="mono">{b.resumen?.total_filas ?? "—"}</td>
                <td className="mono" style={{ color: "var(--ok)" }}>
                  {b.resumen?.validos ?? "—"}
                </td>
                <td className="mono" style={{ color: "var(--warn)" }}>
                  {b.resumen?.advertencias ?? "—"}
                </td>
                <td className="mono" style={{ color: "var(--error)" }}>
                  {b.resumen?.invalidos ?? "—"}
                </td>
                <td>
                  <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                    <Link href={`/imports/${b.id}`} className="btn" style={{ padding: "5px 10px", fontSize: 12 }}>
                      Revisar
                    </Link>
                    <button
                      className="btn btn-danger"
                      style={{ padding: "5px 10px", fontSize: 12 }}
                      onClick={() => handleDelete(b)}
                      disabled={deletingId === b.id}
                    >
                      {deletingId === b.id ? "..." : "Eliminar"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
