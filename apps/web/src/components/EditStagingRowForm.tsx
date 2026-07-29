"use client";

import { useState } from "react";
import { StagingRow, StagingRowUpdate, CatalogItem } from "@/lib/api";

type Catalogs = {
  providers: CatalogItem[];
  areas: CatalogItem[];
  categories: CatalogItem[];
  costCenters: CatalogItem[];
  businessUnits: CatalogItem[];
  companies: CatalogItem[];
  branches: CatalogItem[];
};

const TIPOS_DOCUMENTO = ["Factura", "Nota de Credito", "Nota de Debito", "Factura de credito Pyme"];
const MONEDAS = ["Pesos", "ARS", "USD", "Dolares"];

function toDateInputValue(iso: unknown): string {
  if (!iso) return "";
  const d = new Date(String(iso));
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: number | "";
  options: CatalogItem[];
  onChange: (v: number | undefined) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          padding: "9px 11px",
          color: "var(--text)",
        }}
      >
        <option value="">— Sin definir —</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.nombre}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function EditStagingRowForm({
  row,
  catalogs,
  onSave,
  onCancel,
  saving,
}: {
  row: StagingRow;
  catalogs: Catalogs;
  onSave: (updates: StagingRowUpdate) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const m = row.datos_mapeados;
  const [form, setForm] = useState<StagingRowUpdate>({
    numero_factura: String(m.numero_factura ?? ""),
    fecha_emision: toDateInputValue(m.fecha_emision),
    importe_total: m.importe_total ? Number(m.importe_total) : undefined,
    moneda: String(m.moneda ?? "Pesos"),
    tipo_documento: String(m.tipo_documento ?? "Factura"),
    descripcion: String(m.descripcion ?? ""),
    orden_compra: m.orden_compra ? String(m.orden_compra) : "",
    observaciones: m.observaciones ? String(m.observaciones) : "",
    provider_id: m.provider_id ? Number(m.provider_id) : undefined,
    area_id: m.area_id ? Number(m.area_id) : undefined,
    category_id: m.category_id ? Number(m.category_id) : undefined,
    cost_center_id: m.cost_center_id ? Number(m.cost_center_id) : undefined,
    business_unit_id: m.business_unit_id ? Number(m.business_unit_id) : undefined,
    company_id: m.company_id ? Number(m.company_id) : undefined,
    branch_id: m.branch_id ? Number(m.branch_id) : undefined,
  });

  function set<K extends keyof StagingRowUpdate>(key: K, value: StagingRowUpdate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        <div className="field">
          <label>N° Factura</label>
          <input value={form.numero_factura ?? ""} onChange={(e) => set("numero_factura", e.target.value)} />
        </div>
        <div className="field">
          <label>Fecha de emisión</label>
          <input type="date" value={form.fecha_emision ?? ""} onChange={(e) => set("fecha_emision", e.target.value)} />
        </div>
        <div className="field">
          <label>Tipo de documento</label>
          <select
            value={form.tipo_documento}
            onChange={(e) => set("tipo_documento", e.target.value)}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "9px 11px", color: "var(--text)" }}
          >
            {TIPOS_DOCUMENTO.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Importe total</label>
          <input
            type="number"
            step="0.01"
            value={form.importe_total ?? ""}
            onChange={(e) => set("importe_total", e.target.value ? Number(e.target.value) : undefined)}
          />
        </div>
        <div className="field">
          <label>Moneda</label>
          <select
            value={form.moneda}
            onChange={(e) => set("moneda", e.target.value)}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "9px 11px", color: "var(--text)" }}
          >
            {MONEDAS.map((mo) => (
              <option key={mo} value={mo}>{mo}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Orden de compra</label>
          <input value={form.orden_compra ?? ""} onChange={(e) => set("orden_compra", e.target.value)} />
        </div>

        <Select label="Proveedor" value={form.provider_id ?? ""} options={catalogs.providers} onChange={(v) => set("provider_id", v)} />
        <Select label="Área" value={form.area_id ?? ""} options={catalogs.areas} onChange={(v) => set("area_id", v)} />
        <Select label="Categoría" value={form.category_id ?? ""} options={catalogs.categories} onChange={(v) => set("category_id", v)} />

        <Select label="Centro de costo" value={form.cost_center_id ?? ""} options={catalogs.costCenters} onChange={(v) => set("cost_center_id", v)} />
        <Select label="Unidad de negocio" value={form.business_unit_id ?? ""} options={catalogs.businessUnits} onChange={(v) => set("business_unit_id", v)} />
        <Select label="Empresa" value={form.company_id ?? ""} options={catalogs.companies} onChange={(v) => set("company_id", v)} />

        <Select label="Sucursal" value={form.branch_id ?? ""} options={catalogs.branches} onChange={(v) => set("branch_id", v)} />
      </div>

      <div className="field">
        <label>Descripción</label>
        <input value={form.descripcion ?? ""} onChange={(e) => set("descripcion", e.target.value)} />
      </div>
      <div className="field">
        <label>Observaciones</label>
        <input value={form.observaciones ?? ""} onChange={(e) => set("observaciones", e.target.value)} />
      </div>

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn" onClick={onCancel} disabled={saving}>
          Cancelar
        </button>
        <button className="btn btn-primary" onClick={() => onSave(form)} disabled={saving}>
          {saving ? "Guardando..." : "Guardar cambios"}
        </button>
      </div>
    </div>
  );
}
