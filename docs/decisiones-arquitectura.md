# Decisiones de arquitectura - Control de Gasto Sistemas

Registro breve de decisiones tomadas y su motivo, para no perder el porqué con el tiempo.

| Fecha | Decisión | Motivo |
|---|---|---|
| Etapa 0 | Backend en FastAPI (Python) en vez de NestJS | Procesamiento de CSV y validaciones de datos más naturales en Python; Pydantic da contratos de datos y OpenAPI casi gratis |
| Etapa 0 | Frontend Next.js desplegado en Cloud Run (no Firebase Hosting) | Mantener todo el despliegue bajo un mismo modelo (Cloud Run + Artifact Registry + Terraform) |
| Etapa 0 | Moneda base: ARS | Definido por el usuario |
| Etapa 0 | Login MVP: usuario/contraseña propio, sin SSO | Definido por el usuario; 1 solo usuario en el MVP |
| Etapa 0 | Sin segregación de funciones (subir ≠ aprobar) | Definido por el usuario; 1 solo usuario en el MVP |
| Etapa 0 | Categorías y centros de costo tomados literalmente del CSV real de TSDocs (códigos ST01-ST08, STI03/05/06) | Evita inventar taxonomía; se aprovecha la clasificación contable ya existente en "Cuenta Personal" |
| Etapa 0 | "Cuenta Personal" se parsea en Categoría + Centro de Costo | Definido por el usuario, tras revisar el formato real `GRUPO - DESCRIPCIÓN - CÓDIGO` |
| Etapa 0 | Empresa y Sucursal como dimensiones filtrables nuevas | Definido por el usuario; permiten acumulados por razón social y por sede específica |
| Etapa 0 | "Sistemas Inversiones" tratado como categoría más, sin flag de CapEx | Definido por el usuario, para no sumar complejidad al MVP |
| Etapa 0 | Área "Seguridad" no se crea por separado; se computa en "Mesa de Servicio" | Definido por el usuario |
| Etapa 0 | Acumulado real por proveedor: neteo por Tipo de Documento (Factura/Fact. Crédito Pyme suman, Nota Crédito resta, Nota Débito suma) | Refleja el gasto real sin necesitar vincular manualmente cada nota a su factura de origen |
| Etapa 1 | Cloud SQL con IP pública + Cloud SQL Auth Proxy nativo de Cloud Run (sin VPC) | Simplifica la infraestructura para un MVP de 1 usuario; se puede migrar a IP privada + VPC connector más adelante si crece el equipo |
| Etapa 1 | CI/CD con clave de Service Account (JSON) en GitHub Secrets, no Workload Identity Federation | Más simple de configurar para el primer despliegue; queda anotado como mejora de seguridad futura |
| Etapa 1 | `tier = db-f1-micro`, `availability_type = ZONAL` en Cloud SQL | Dimensionado para 1 usuario; subir a un tier mayor y a REGIONAL si se suman más usuarios o se requiere alta disponibilidad |
