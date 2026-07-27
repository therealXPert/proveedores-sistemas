resource "google_cloud_run_v2_service" "api" {
  name     = "control-gasto-api"
  location = var.region

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = 0
      max_instance_count = 2 # MVP 1 usuario, no hace falta mas
    }

    containers {
      image = var.image
      ports {
        container_port = 8080
      }

      env {
        name  = "DB_INSTANCE_CONNECTION_NAME"
        value = var.db_connection_name
      }
      env {
        name  = "DB_NAME"
        value = var.db_name
      }
      env {
        name  = "DB_USER"
        value = var.db_user
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = "db-password"
            version = "latest"
          }
        }
      }
      env {
        name = "APP_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "app-secret-key"
            version = "latest"
          }
        }
      }
      env {
        name  = "GCS_BUCKET"
        value = var.gcs_bucket
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.db_connection_name]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = var.invoker_member
}
