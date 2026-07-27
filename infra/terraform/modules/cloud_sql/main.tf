resource "google_sql_database_instance" "instance" {
  name             = var.instance_name
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.tier
    availability_type = var.availability_type
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }

    ip_configuration {
      ipv4_enabled = true
      # Sin redes autorizadas abiertas: Cloud Run se conecta via socket unix
      # usando el Cloud SQL Auth Proxy embebido (conector nativo de Cloud Run).
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.instance.name
}

resource "google_sql_user" "app_user" {
  name     = var.db_user
  instance = google_sql_database_instance.instance.name
  password = var.db_password
}
