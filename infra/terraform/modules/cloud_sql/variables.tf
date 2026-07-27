variable "instance_name" {
  type    = string
  default = "control-gasto-sistemas-db"
}
variable "region" {
  type = string
}
variable "tier" {
  type    = string
  default = "db-f1-micro" # dev/MVP con 1 usuario. Subir a db-custom-1-3840 en prod si hace falta.
}
variable "availability_type" {
  type    = string
  default = "ZONAL" # usar REGIONAL en prod para alta disponibilidad
}
variable "database_name" {
  type    = string
  default = "control_gasto"
}
variable "db_user" {
  type    = string
  default = "app_user"
}
variable "db_password" {
  type      = string
  sensitive = true
}
