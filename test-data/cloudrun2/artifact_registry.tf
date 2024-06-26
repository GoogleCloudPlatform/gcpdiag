data "google_client_config" "default" {
}

data "google_client_openid_userinfo" "me" {
}

resource "google_artifact_registry_repository" "cloudrun_repo" {

  project       = google_project.project.project_id
  location      = "us-central1"
  repository_id = "cloudrun-repository"
  format        = "DOCKER"
}


locals {
  repository_url = "${google_artifact_registry_repository.cloudrun_repo.location}-docker.pkg.dev/${google_project.project.project_id}/${google_artifact_registry_repository.cloudrun_repo.repository_id}"
}
