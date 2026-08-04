"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useGroup } from "@/lib/group-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/imports", label: "Importaciones" },
  { href: "/reportes", label: "Reportes" },
  { href: "/presupuesto", label: "Presupuesto" },
  { href: "/proveedores", label: "Proveedores" },
  { href: "/categorias", label: "Categorías" },
  { href: "/areas", label: "Áreas" },
  { href: "/grupos-economicos", label: "Grupos Económicos" },
  { href: "/auditoria", label: "Auditoría" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { groups, activeGroupId, setActiveGroupId } = useGroup();

  return (
    <aside
      style={{
        width: "var(--sidebar-w)",
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        padding: "20px 0",
        height: "100vh",
        position: "sticky",
        top: 0,
      }}
    >
      <div style={{ padding: "0 20px", marginBottom: 18 }}>
        <div className="eyebrow" style={{ marginBottom: 4 }}>
          Autocity · Sistemas
        </div>
        <div className="h2">Control de Gasto</div>
      </div>

      <div style={{ padding: "0 20px", marginBottom: 20 }}>
        <label className="faint" style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", display: "block", marginBottom: 6 }}>
          Grupo económico
        </label>
        <select
          value={activeGroupId ?? ""}
          onChange={(e) => setActiveGroupId(e.target.value ? Number(e.target.value) : null)}
          style={{
            width: "100%",
            background: "var(--surface-raised)",
            border: "1px solid var(--accent-dim)",
            borderRadius: "var(--radius)",
            padding: "7px 8px",
            color: "var(--text)",
            fontSize: 12.5,
            fontWeight: 600,
          }}
        >
          <option value="">Todos los grupos</option>
          {groups.map((g) => (
            <option key={g.id} value={g.id}>{g.nombre}</option>
          ))}
        </select>
      </div>

      <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
        {NAV_ITEMS.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: "9px 20px",
                fontSize: 13,
                fontWeight: 550,
                color: active ? "var(--text)" : "var(--text-dim)",
                borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
                background: active ? "var(--surface)" : "transparent",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div style={{ padding: "16px 20px 0", borderTop: "1px solid var(--border)" }}>
        <div className="mono" style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 2 }}>
          {user?.email}
        </div>
        <div className="faint" style={{ fontSize: 11, marginBottom: 10 }}>
          {user?.roles?.join(", ")}
        </div>
        <button onClick={logout} className="btn" style={{ width: "100%", justifyContent: "center", fontSize: 12, padding: "6px 10px" }}>
          Salir
        </button>
      </div>
    </aside>
  );
}
