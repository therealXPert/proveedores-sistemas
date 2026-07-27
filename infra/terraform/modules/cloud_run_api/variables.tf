variable "region" { type = string }
variable "service_account_email" { type = string }
variable "image" { type = string }
variable "db_connection_name" { type = string }
variable "db_name" { type = string }
variable "db_user" { type = string }
variable "gcs_bucket" { type = string }
variable "invoker_member" {
  type    = string
  default = "allUsers" # MVP con 1 usuario: se restringe a IAP o cuenta especifica antes de sumar mas usuarios
}
