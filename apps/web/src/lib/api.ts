const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData) && options.body) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      // respuesta sin JSON (ej. error de infraestructura)
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () =>
    request<{ id: number; email: string; nombre: string; roles: string[] }>("/auth/me"),

  listImports: () => request<ImportBatch[]>("/imports"),

  getImport: (id: number) => request<ImportBatch>(`/imports/${id}`),

  uploadImport: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<ImportBatch>("/imports/upload", { method: "POST", body: formData });
  },

  previewImport: (id: number) => request<StagingRow[]>(`/imports/${id}/preview`),

  approveImport: (id: number) =>
    request<{ filas_aprobadas: number; filas_excluidas_por_error: number }>(
      `/imports/${id}/approve`,
      { method: "POST", body: "" }
    ),

  rejectImport: (id: number, motivo?: string) =>
    request<{ estado: string }>(`/imports/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ motivo }),
    }),
};

export type ImportBatchSummary = {
  validos: number;
  advertencias: number;
  invalidos: number;
  duplicados: number;
  total_filas: number;
  columnas_desconocidas: string[];
  encoding_detectado: string | null;
  separador_detectado: string | null;
};

export type ImportBatch = {
  id: number;
  estado: string;
  resumen: ImportBatchSummary | null;
  created_at: string;
};

export type ValidationErrorOut = {
  tipo: string;
  severidad: "bloqueante" | "advertencia" | "info";
  mensaje: string;
};

export type StagingRow = {
  id: number;
  estado_fila: "valida" | "advertencia" | "error" | "excluida";
  datos_mapeados: Record<string, unknown>;
  errores: ValidationErrorOut[];
};
