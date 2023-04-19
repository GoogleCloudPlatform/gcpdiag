resource "google_storage_bucket" "dataflow_out" {
  name          = "dataflow_out_${random_string.project_id_suffix.id}"
  location      = "US"
  force_destroy = true
  project       = google_project.project.project_id
}
