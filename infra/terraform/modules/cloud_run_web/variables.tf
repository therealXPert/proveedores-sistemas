variable "region" { type = string }
variable "service_account_email" { type = string }
variable "image" { type = string }
variable "api_url" { type = string }
variable "invoker_member" {
  type    = string
  default = "allUsers"
}
