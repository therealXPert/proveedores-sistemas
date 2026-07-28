const ESTADO_MAP: Record<string, { label: string; cls: string }> = {
  recibido: { label: "Recibido", cls: "status-neutral" },
  procesando: { label: "Procesando", cls: "status-info" },
  pendiente_validacion: { label: "Pendiente de validación", cls: "status-warn" },
  con_errores: { label: "Con errores", cls: "status-error" },
  validado: { label: "Validado", cls: "status-info" },
  aprobado: { label: "Aprobado", cls: "status-ok" },
  rechazado: { label: "Rechazado", cls: "status-error" },
  anulado: { label: "Anulado", cls: "status-neutral" },
  // filas de staging
  valida: { label: "Válida", cls: "status-ok" },
  advertencia: { label: "Advertencia", cls: "status-warn" },
  error: { label: "Error", cls: "status-error" },
  excluida: { label: "Excluida", cls: "status-neutral" },
};

export default function StatusBadge({ estado }: { estado: string }) {
  const info = ESTADO_MAP[estado] || { label: estado, cls: "status-neutral" };
  return <span className={`status ${info.cls}`}>{info.label}</span>;
}
