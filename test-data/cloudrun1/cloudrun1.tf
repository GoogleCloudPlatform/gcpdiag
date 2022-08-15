resource "google_cloud_run_service" "default" {
  project  = google_project.project.project_id
  name     = "cloudrun1"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
