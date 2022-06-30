resource "google_storage_bucket" "bucket_with_retention" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcb1-bucket1-${random_string.project_id_suffix.id}"
  location      = "US"
  storage_class = "STANDARD"
  retention_policy {
    retention_period = 10
  }
}

output "bucket_with_retention" {
  value = google_storage_bucket.bucket_with_retention.name
}
