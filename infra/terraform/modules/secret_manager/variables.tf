variable "secret_names" {
  type        = list(string)
  description = "Nombres de los secretos a crear. No es sensible, solo son claves; se usa para el for_each porque Terraform no permite valores sensibles ahi."
  default = [
    "db-password",
    "app-secret-key"
  ]
}

variable "secret_values" {
  type        = map(string)
  sensitive   = true
  description = "Mapa secret_id -> valor inicial del secreto. Debe tener una entrada para cada nombre en secret_names."
}
