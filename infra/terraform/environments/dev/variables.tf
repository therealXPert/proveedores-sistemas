variable "project_id" {
  type        = string
  description = "ID del proyecto de GCP de Autocity"
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "db_password" {
  type        = string
  sensitive   = true
  description = "Password inicial del usuario de base de datos"
}
variable "api_image" {
  type    = string
  default = ""
}
variable "web_image" {
  type    = string
  default = ""
}
