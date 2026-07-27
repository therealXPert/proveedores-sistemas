locals {
  api_image = var.api_image != "" ? var.api_image : "us-docker.pkg.dev/cloudrun/container/hello"
  web_image = var.web_image != "" ? var.web_image : "us-docker.pkg.dev/cloudrun/container/hello"
}

module "artifact_registry" {
  source     = "../../modules/artifact_registry"
  region     = var.region
  project_id = var.project_id
}

module "secret_manager" {
  source = "../../modules/secret_manager"
  secret_values = {
    "db-password"    = var.db_password
    "app-secret-key" = random_password.app_secret_key.result
  }
}

resource "random_password" "app_secret_key" {
  length  = 64
  special = false
}

module "cloud_storage" {
  source      = "../../modules/cloud_storage"
  region      = var.region
  bucket_name = "${var.project_id}-facturas-sistemas"
}

module "cloud_sql" {
  source      = "../../modules/cloud_sql"
  region      = var.region
  db_password = var.db_password
}

module "iam" {
  source     = "../../modules/iam"
  project_id = var.project_id
}

module "cloud_run_api" {
  source                = "../../modules/cloud_run_api"
  region                = var.region
  service_account_email = module.iam.service_account_email
  image                 = local.api_image
  db_connection_name    = module.cloud_sql.connection_name
  db_name               = "control_gasto"
  db_user               = "app_user"
  gcs_bucket            = module.cloud_storage.bucket_name

  depends_on = [module.secret_manager]
}

module "cloud_run_web" {
  source                = "../../modules/cloud_run_web"
  region                = var.region
  service_account_email = module.iam.service_account_email
  image                 = local.web_image
  api_url               = module.cloud_run_api.url
}
