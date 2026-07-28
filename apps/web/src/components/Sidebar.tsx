"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/imports", label: "Importaciones" },
  // Los siguientes se habilitan en proximas etapas del proyecto:
  // { href: "/facturas", label: "Facturas" },
  // { href: "/proveedores", label: "Proveedores" },
  // { href: "/presupuesto", label: "Presupuesto" },
  // { href: "/reportes", label: "Reportes" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

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
      <div style={{ padding: "0 20px", marginBottom: 28 }}>
        <div className="eyebrow" style={{ marginBottom: 4 }}>
          Autocity · Sistemas
        </div>
        <div className="h2">Control de Gasto</div>
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
