resource "google_storage_bucket" "csv_originals" {
  name                        = var.bucket_name
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 730 # 2 años
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
}
