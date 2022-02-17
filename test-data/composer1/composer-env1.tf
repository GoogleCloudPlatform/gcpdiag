resource "google_composer_environment" "env1" {
  name    = "env1"
  region  = "us-central1"
  project = google_project.project.project_id

  depends_on = [google_project_service.composer]
}
