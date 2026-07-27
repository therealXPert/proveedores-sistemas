# Control de Gasto - Sistemas (Autocity)

Etapa 1: infraestructura base en GCP + esqueleto de repo + CI/CD.

Esta guía asume que partís de cero. Cada paso indica el comando exacto y qué deberías ver si salió bien.

---

## 0. Prerrequisitos (una sola vez)

1. Tener una cuenta de Google con acceso al proyecto de GCP de Autocity (o crear uno nuevo).
2. Instalar en tu máquina:
   - **Google Cloud CLI**: https://cloud.google.com/sdk/docs/install
   - **Terraform** (>= 1.5): https://developer.hashicorp.com/terraform/install
   - **Docker Desktop**: https://www.docker.com/products/docker-desktop/
   - **Git**
3. Verificar instalación:
   ```bash
   gcloud --version
   terraform --version
   docker --version
   git --version
   ```

---

## 1. Crear/seleccionar el proyecto de GCP

Si ya tenés un proyecto de GCP para esto, anotá su **Project ID** (no el nombre, el ID, ej. `autocity-control-gasto-dev`) y saltá al paso 2.

Si necesitás crear uno nuevo:

```bash
gcloud projects create autocity-control-gasto-dev --name="Control de Gasto Sistemas"
gcloud config set project autocity-control-gasto-dev
```

Vinculá una cuenta de facturación (necesario para usar Cloud Run/Cloud SQL):

```bash
gcloud billing accounts list
gcloud billing projects link autocity-control-gasto-dev --billing-account=CUENTA_DE_FACTURACION_ID
```

---

## 2. Habilitar las APIs necesarias

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  --project=autocity-control-gasto-dev
```

Esto tarda 1-2 minutos. No debería dar error.

---

## 3. Crear el bucket de estado de Terraform

Terraform necesita un lugar remoto para guardar su "estado" (qué recursos ya creó). Se crea una sola vez, a mano:

```bash
gcloud storage buckets create gs://autocity-control-gasto-dev-tfstate \
  --project=autocity-control-gasto-dev \
  --location=us-central1 \
  --uniform-bucket-level-access

gcloud storage buckets update gs://autocity-control-gasto-dev-tfstate --versioning
```

Reemplazá `autocity-control-gasto-dev` por tu Project ID real en ambos comandos.

Luego editá `infra/terraform/environments/dev/backend.tf` y reemplazá:
```hcl
bucket = "AUTOCITY_PROJECT_ID-tfstate"
```
por:
```hcl
bucket = "autocity-control-gasto-dev-tfstate"
```

---

## 4. Configurar las variables de Terraform

```bash
cd infra/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
```

Editá `terraform.tfvars` con tus datos reales:
```hcl
project_id  = "autocity-control-gasto-dev"
region      = "us-central1"
db_password = "elegí-una-contraseña-segura-acá"
```

**Importante:** `terraform.tfvars` contiene una contraseña — no lo subas a Git. Ya está incluido en `.gitignore` (ver paso 8, más abajo).

---

## 5. Autenticarte y aplicar Terraform

```bash
gcloud auth application-default login
```

Esto abre el navegador para loguearte con tu cuenta de Google.

Luego, desde `infra/terraform/environments/dev`:

```bash
terraform init
terraform plan
```

Revisá el plan: deberías ver `Plan: 15 to add, 0 to change, 0 to destroy` (Artifact Registry, 2x Cloud Run + sus permisos, Cloud SQL con su base de datos y usuario, Cloud Storage, la Service Account con sus 3 asignaciones de rol, y los 2 secretos de Secret Manager con su valor inicial — son 7 piezas de infraestructura pero 15 recursos individuales, porque algunas piezas como Cloud SQL o IAM se componen de varios recursos). Si todo se ve razonable:

```bash
terraform apply -auto-approve
```

> **Si usás Git Bash / MINGW64 en Windows**: usá siempre `-auto-approve`. La confirmación interactiva (`Enter a value: yes`) suele fallar con un error `EOF` en esa terminal, y si lo interrumpís a mitad de camino el estado puede quedar bloqueado (ver recuadro de recuperación más abajo).

**Esto tarda entre 5 y 10 minutos** (Cloud SQL es lo que más demora).

Al terminar vas a ver algo como:
```
Outputs:

api_url = "https://control-gasto-api-xxxxx-rj.a.run.app"
web_url = "https://control-gasto-web-xxxxx-rj.a.run.app"
artifact_registry_url = "us-central1-docker.pkg.dev/autocity-control-gasto-dev/control-gasto-sistemas"
db_connection_name = "autocity-control-gasto-dev:us-central1:control-gasto-sistemas-db"
```

**Guardá estos 4 valores**, los vas a necesitar.

En este punto, `api_url` y `web_url` van a mostrar la imagen placeholder ("hello") porque todavía no subimos nuestro propio código — eso lo hace el pipeline de CI/CD en el paso 6.

Los secretos (`db-password`, `app-secret-key`) ya quedan creados **con su valor** en este mismo paso — Terraform genera `app-secret-key` automáticamente (una clave al azar) y usa el `db_password` que pusiste en `terraform.tfvars` para `db-password`. No hace falta cargarlos a mano.

### Si el `apply` se corta o queda "trabado"

Dos errores típicos si se interrumpe un `apply` (por ejemplo por el problema de `-auto-approve` en Git Bash) y cómo resolverlos:

**a) `Error acquiring the state lock`** — el estado quedó bloqueado por un intento anterior interrumpido:
```bash
terraform force-unlock -force ID_DEL_LOCK_QUE_APARECE_EN_EL_ERROR
```

**b) `Secret ... already exists` / `... resource already exists`** — un recurso se llegó a crear en GCP en un intento anterior, pero por la interrupción no quedó registrado en el estado de Terraform. Comprobá qué existe y en qué estado quedó cada uno:
```bash
gcloud secrets list --project=TU_PROJECT_ID
```
Si un secreto ya existe en GCP pero Terraform quiere volver a crearlo, importalo al estado en vez de borrarlo:
```bash
terraform import 'module.secret_manager.google_secret_manager_secret.secret["db-password"]' \
  projects/TU_PROJECT_ID/secrets/db-password
```
(reemplazá `db-password` por el nombre del secreto que corresponda). Después de importar, volvé a correr `terraform apply -auto-approve`.

---

## 6. Subir el código a GitHub y configurar CI/CD

### 7.1 Crear el repositorio en GitHub

```bash
cd /ruta/donde/tengas/autocity-control-gasto
git init
git add .
git commit -m "Etapa 1: infraestructura y esqueleto de repo"
```

Creá un repo vacío en GitHub (por la web, sin README) y luego:

```bash
git remote add origin https://github.com/TU_USUARIO/autocity-control-gasto.git
git branch -M main
git push -u origin main
```

### 7.2 Crear la Service Account para GitHub Actions

```bash
gcloud iam service-accounts create github-actions-deploy \
  --display-name="GitHub Actions Deploy" \
  --project=autocity-control-gasto-dev

gcloud projects add-iam-policy-binding autocity-control-gasto-dev \
  --member="serviceAccount:github-actions-deploy@autocity-control-gasto-dev.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding autocity-control-gasto-dev \
  --member="serviceAccount:github-actions-deploy@autocity-control-gasto-dev.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding autocity-control-gasto-dev \
  --member="serviceAccount:github-actions-deploy@autocity-control-gasto-dev.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Generar la clave (archivo JSON) que va a usar GitHub Actions
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-deploy@autocity-control-gasto-dev.iam.gserviceaccount.com
```

Esto genera un archivo `github-actions-key.json` en tu carpeta actual. **No lo subas a Git.**

> Nota de seguridad: usar una clave JSON es la forma más simple para arrancar. Más adelante conviene migrar a Workload Identity Federation (sin claves de larga duración). Lo dejamos anotado como mejora futura, no bloquea el MVP.

### 7.3 Cargar los secretos en GitHub

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Crear:

- `GCP_PROJECT_ID` → el Project ID (ej. `autocity-control-gasto-dev`)
- `GCP_SA_KEY` → pegar el **contenido completo** del archivo `github-actions-key.json`

Después de copiar el contenido, borrá el archivo local:
```bash
rm github-actions-key.json
```

### 7.4 Disparar el primer despliegue real

```bash
git commit --allow-empty -m "Disparar primer despliegue"
git push
```

Andá a la pestaña **Actions** de tu repo en GitHub y mirá el workflow correr. Tarda unos 3-5 minutos. Si termina en verde, `api_url` y `web_url` ya van a servir tu código real (no el placeholder).

---

## 7. Verificar que todo funciona

```bash
curl https://control-gasto-api-xxxxx-rj.a.run.app/health
# Esperado: {"status":"ok"}
```

Abrí `web_url` en el navegador: deberías ver la página "Control de Gasto - Sistemas" con la URL de la API mostrada abajo.

---

## 8. .gitignore (ya incluido)

El repo ya trae un `.gitignore` que excluye `terraform.tfvars`, `node_modules`, `.next`, `__pycache__`, y archivos de claves. Revisalo antes del primer commit si agregás algo nuevo.

---

## Costos aproximados (MVP, 1 usuario)

Con `db-f1-micro` (Cloud SQL) y Cloud Run en `min_instance_count = 0`, el costo mensual esperado para este MVP con 1 usuario está en el orden de **USD 10-25/mes** (mayormente Cloud SQL, que es lo único que corre 24/7). Cloud Run con scale-to-zero no cobra cuando nadie lo usa.

---

## Próximos pasos

Con esto desplegado, la **Etapa 2** agrega el modelo de datos (migraciones Alembic) y el login con usuario/contraseña.
