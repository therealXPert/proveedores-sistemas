resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Imagenes de contenedores - Control de Gasto Sistemas"
  format        = "DOCKER"
}
