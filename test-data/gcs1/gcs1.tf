resource "google_storage_bucket" "gcs1bucket" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcs1bucket-${random_string.project_id_suffix.id}"
  location      = "US"
  storage_class = "STANDARD"
}

resource "google_storage_bucket" "gcs1bucket-labels" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcs1bucket-labels-${random_string.project_id_suffix.id}"
  location      = "US"
  storage_class = "STANDARD"
  labels = {
    "label1" = "value1"
  }
}

resource "google_storage_bucket" "bucket_with_retention" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcs1bucket2-${random_string.project_id_suffix.id}"
  location      = "US"
  storage_class = "STANDARD"
  retention_policy {
    retention_period = 10
  }
}

output "bucket_with_retention" {
  value = google_storage_bucket.bucket_with_retention.name
}
