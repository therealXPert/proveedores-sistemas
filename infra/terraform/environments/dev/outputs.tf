output "api_url" {
  value = module.cloud_run_api.url
}
output "web_url" {
  value = module.cloud_run_web.url
}
output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}
output "db_connection_name" {
  value = module.cloud_sql.connection_name
}
