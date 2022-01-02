resource "google_storage_bucket" "gcs1bucket" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcs1bucket-${random_string.project_id_suffix.id}"
  location      = "US"
  storage_class = "STANDARD"
}
