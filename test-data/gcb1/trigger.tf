resource "google_cloudbuild_trigger" "trigger" {
  project = google_project.project.project_id
  trigger_template {
    branch_name = "main"
    repo_name   = "test-repo"
  }
  build {
    step {
      name = "gcr.io/cloud-builders/gcloud"
    }
  }
  depends_on = [google_project_service.cloudbuild]
}
