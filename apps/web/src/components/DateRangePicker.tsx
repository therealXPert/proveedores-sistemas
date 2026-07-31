"use client";

import { useState } from "react";

export type Rango = { desde: string; hasta: string };

function fmt(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function primerDiaMes(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function ultimoDiaMes(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

export function presetEsteMes(hoy = new Date()): Rango {
  return { desde: fmt(primerDiaMes(hoy)), hasta: fmt(ultimoDiaMes(hoy)) };
}

export function presetEsteAnio(hoy = new Date()): Rango {
  return { desde: `${hoy.getFullYear()}-01-01`, hasta: `${hoy.getFullYear()}-12-31` };
}

export function presetUltimos6Meses(hoy = new Date()): Rango {
  const desde = new Date(hoy.getFullYear(), hoy.getMonth() - 5, 1);
  return { desde: fmt(desde), hasta: fmt(ultimoDiaMes(hoy)) };
}

const PRESETS = [
  { label: "Este mes", fn: presetEsteMes },
  { label: "Este año", fn: presetEsteAnio },
  { label: "Últimos 6 meses", fn: presetUltimos6Meses },
];

export default function DateRangePicker({
  value,
  onChange,
  referencia,
}: {
  value: Rango;
  onChange: (r: Rango) => void;
  /** Fecha de referencia para calcular los atajos (por default, hoy; se puede pasar el último mes con datos). */
  referencia?: Date;
}) {
  const [personalizado, setPersonalizado] = useState(false);

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {PRESETS.map((p) => (
        <button
          key={p.label}
          className="btn"
          style={{ fontSize: 12.5, padding: "6px 12px" }}
          onClick={() => {
            setPersonalizado(false);
            onChange(p.fn(referencia));
          }}
        >
          {p.label}
        </button>
      ))}
      <button
        className={`btn ${personalizado ? "btn-primary" : ""}`}
        style={{ fontSize: 12.5, padding: "6px 12px" }}
        onClick={() => setPersonalizado(true)}
      >
        Personalizado
      </button>

      {personalizado && (
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input
            type="date"
            value={value.desde}
            onChange={(e) => onChange({ ...value, desde: e.target.value })}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "6px 8px", color: "var(--text)", fontSize: 12.5 }}
          />
          <span className="faint" style={{ fontSize: 12 }}>a</span>
          <input
            type="date"
            value={value.hasta}
            onChange={(e) => onChange({ ...value, hasta: e.target.value })}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "6px 8px", color: "var(--text)", fontSize: 12.5 }}
          />
        </div>
      )}
    </div>
  );
}
