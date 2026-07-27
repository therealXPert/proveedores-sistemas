resource "google_secret_manager_secret" "secret" {
  for_each  = toset(var.secret_names)
  secret_id = each.value

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "version" {
  for_each    = toset(var.secret_names)
  secret      = google_secret_manager_secret.secret[each.key].id
  secret_data = var.secret_values[each.key]
}
