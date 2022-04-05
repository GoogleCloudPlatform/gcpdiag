resource "google_artifact_registry_repository" "gcb1_repo" {
  provider = google-beta

  project       = google_project.project.project_id
  location      = "us-central1"
  repository_id = "gcb1-repository"
  description   = "example docker repository"
  format        = "DOCKER"
}

resource "google_artifact_registry_repository_iam_binding" "binding" {
  provider   = google-beta
  project    = google_artifact_registry_repository.gcb1_repo.project
  location   = google_artifact_registry_repository.gcb1_repo.location
  repository = google_artifact_registry_repository.gcb1_repo.name
  role       = "roles/artifactregistry.admin"
  members = [
    "serviceAccount:${google_service_account.service_account_custom2.email}",
  ]
}

locals {
  repository_url = "${google_artifact_registry_repository.gcb1_repo.location}-docker.pkg.dev/${google_project.project.project_id}/${google_artifact_registry_repository.gcb1_repo.repository_id}"
}

output "artifact_registry" {
  value = google_artifact_registry_repository.gcb1_repo.id
}
