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
    request<{ filas_rechazadas: number }>(`/imports/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ motivo }),
    }),

  approveRow: (stagingId: number) =>
    request<{ staging_id: number; invoice_id: number; resultado: string }>(
      `/imports/staging/${stagingId}/approve`,
      { method: "POST", body: "" }
    ),

  rejectRow: (stagingId: number, motivo?: string) =>
    request<{ staging_id: number; resultado: string }>(`/imports/staging/${stagingId}/reject`, {
      method: "POST",
      body: JSON.stringify({ motivo }),
    }),

  updateRow: (stagingId: number, updates: StagingRowUpdate) =>
    request<StagingRow>(`/imports/staging/${stagingId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    }),

  listProviders: () => request<CatalogItem[]>("/catalogs/providers"),
  listAreas: () => request<CatalogItem[]>("/catalogs/areas"),
  listCategories: () => request<CatalogItem[]>("/catalogs/categories"),
  listCostCenters: () => request<CatalogItem[]>("/catalogs/cost-centers"),
  listBusinessUnits: () => request<CatalogItem[]>("/catalogs/business-units"),
  listCompanies: () => request<CatalogItem[]>("/catalogs/companies"),
  listBranches: () => request<CatalogItem[]>("/catalogs/branches"),

  deleteImport: (id: number) =>
    request<{ eliminado: boolean; facturas_eliminadas: number }>(`/imports/${id}`, { method: "DELETE" }),

  // --- Administracion de proveedores ---
  listProvidersAdmin: () => request<Provider[]>("/providers"),
  getProvider: (id: number) => request<Provider>(`/providers/${id}`),
  updateProvider: (id: number, updates: ProviderUpdate) =>
    request<Provider>(`/providers/${id}`, { method: "PATCH", body: JSON.stringify(updates) }),
  addProviderAlias: (id: number, alias_texto: string) =>
    request<{ id: number; alias_texto: string }>(`/providers/${id}/aliases`, {
      method: "POST",
      body: JSON.stringify({ alias_texto }),
    }),
  deleteProviderAlias: (aliasId: number) =>
    request<{ eliminado: boolean }>(`/providers/aliases/${aliasId}`, { method: "DELETE" }),
  mergeProviders: (targetId: number, otherProviderId: number) =>
    request<{ facturas_reasignadas: number; alias_reasignados: number; presupuestos_reasignados: number }>(
      `/providers/${targetId}/merge`,
      { method: "POST", body: JSON.stringify({ other_provider_id: otherProviderId }) }
    ),

  // --- Categorias ---
  listCategoriesAdmin: () => request<Category[]>("/admin/categories"),
  createCategory: (payload: CategoryUpdate & { nombre: string }) =>
    request<Category>("/admin/categories", { method: "POST", body: JSON.stringify(payload) }),
  updateCategory: (id: number, payload: CategoryUpdate) =>
    request<Category>(`/admin/categories/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deactivateCategory: (id: number) =>
    request<{ desactivada: boolean }>(`/admin/categories/${id}`, { method: "DELETE" }),

  // --- Areas ---
  listAreasAdmin: () => request<AreaAdmin[]>("/admin/areas"),
  createArea: (nombre_normalizado: string) =>
    request<AreaAdmin>("/admin/areas", { method: "POST", body: JSON.stringify({ nombre_normalizado }) }),
  updateArea: (id: number, nombre_normalizado: string) =>
    request<AreaAdmin>(`/admin/areas/${id}`, { method: "PATCH", body: JSON.stringify({ nombre_normalizado }) }),
  deactivateArea: (id: number) =>
    request<{ desactivada: boolean }>(`/admin/areas/${id}`, { method: "DELETE" }),
  addAreaAlias: (id: number, alias_texto: string) =>
    request<{ id: number; alias_texto: string }>(`/admin/areas/${id}/aliases`, {
      method: "POST",
      body: JSON.stringify({ alias_texto }),
    }),
  deleteAreaAlias: (aliasId: number) =>
    request<{ eliminado: boolean }>(`/admin/areas/aliases/${aliasId}`, { method: "DELETE" }),

  // --- Presupuesto ---
  listBudgets: (anio: number) => request<BudgetItem[]>(`/budgets?anio=${anio}`),
  createBudget: (payload: BudgetCreate) =>
    request<BudgetItem>("/budgets", { method: "POST", body: JSON.stringify(payload) }),
  updateBudget: (id: number, payload: BudgetUpdatePayload) =>
    request<BudgetItem>(`/budgets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteBudget: (id: number) => request<{ eliminado: boolean }>(`/budgets/${id}`, { method: "DELETE" }),
  budgetResumen: (anio: number) => request<BudgetResumenItem[]>(`/budgets/resumen?anio=${anio}`),
};

export type Category = {
  id: number;
  nombre: string;
  codigo_erp: string | null;
  categoria_padre_id: number | null;
  categoria_padre_nombre: string | null;
  is_active: boolean;
};

export type CategoryUpdate = {
  nombre?: string;
  codigo_erp?: string;
  categoria_padre_id?: number;
};

export type AreaAdmin = {
  id: number;
  nombre_normalizado: string;
  is_active: boolean;
  aliases: { id: number; alias_texto: string }[];
  cantidad_facturas: number;
};

export type BudgetItem = {
  id: number;
  anio: number;
  mes: number | null;
  provider_id: number | null;
  provider_nombre: string | null;
  area_id: number | null;
  area_nombre: string | null;
  category_id: number | null;
  category_nombre: string | null;
  cost_center_id: number | null;
  cost_center_nombre: string | null;
  business_unit_id: number | null;
  business_unit_nombre: string | null;
  moneda: string;
  periodicidad_original: string | null;
  importe_original: number | null;
  importe_mensual_equivalente: number | null;
  comentario: string | null;
};

export type BudgetCreate = {
  anio: number;
  mes?: number;
  provider_id?: number;
  area_id?: number;
  category_id?: number;
  cost_center_id?: number;
  business_unit_id?: number;
  moneda?: string;
  periodicidad_original?: string;
  importe_original?: number;
  comentario?: string;
};

export type BudgetUpdatePayload = {
  provider_id?: number;
  area_id?: number;
  category_id?: number;
  cost_center_id?: number;
  business_unit_id?: number;
  periodicidad_original?: string;
  importe_original?: number;
  comentario?: string;
};

export type BudgetResumenItem = {
  provider_id: number;
  provider_nombre: string;
  presupuesto_mensual: number;
  gasto_real_promedio_mensual: number;
  gasto_real_total: number;
  desvio_mensual: number;
};

export type Provider = {
  id: number;
  nombre_normalizado: string;
  razon_social: string | null;
  cuit: string | null;
  categoria_principal_id: number | null;
  categoria_principal_nombre: string | null;
  moneda_habitual: string | null;
  condiciones_comerciales: string | null;
  observaciones: string | null;
  aliases: { id: number; alias_texto: string }[];
  cantidad_facturas: number;
};

export type ProviderUpdate = {
  nombre_normalizado?: string;
  razon_social?: string;
  cuit?: string;
  categoria_principal_id?: number;
  moneda_habitual?: string;
  condiciones_comerciales?: string;
  observaciones?: string;
};

export type CatalogItem = { id: number; nombre: string };

export type StagingRowUpdate = {
  numero_factura?: string;
  fecha_emision?: string;
  importe_total?: number;
  moneda?: string;
  tipo_documento?: string;
  descripcion?: string;
  orden_compra?: string;
  observaciones?: string;
  provider_id?: number;
  area_id?: number;
  category_id?: number;
  cost_center_id?: number;
  business_unit_id?: number;
  company_id?: number;
  branch_id?: number;
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
  estado_fila: "valida" | "advertencia" | "error";
  resultado: "pendiente" | "aprobada" | "rechazada";
  invoice_id: number | null;
  motivo_rechazo: string | null;
  datos_mapeados: Record<string, unknown>;
  errores: ValidationErrorOut[];
};
