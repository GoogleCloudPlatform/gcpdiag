resource "google_composer_environment" "good" {
  name    = "good"
  region  = "us-central1"
  project = google_project.project.project_id
}
