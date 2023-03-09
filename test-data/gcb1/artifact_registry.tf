data "google_client_config" "default" {
}

data "google_client_openid_userinfo" "me" {
}

resource "google_artifact_registry_repository" "gcb1_repo" {
  provider = google-beta

  project       = google_project.project.project_id
  location      = "us-central1"
  repository_id = "gcb1-repository"
  description   = "example docker repository"
  format        = "DOCKER"
}

//   https://cloud.google.com/artifact-registry/docs/transition/setup-gcr-repo#redirect-enable
resource "google_artifact_registry_repository" "legacy" {
  location      = "us"
  project       = google_project.project.project_id
  description   = "gcr.io repository"
  format        = "DOCKER"
  repository_id = "gcr.io"
}


resource "google_project_iam_binding" "storageAdmin" {
  project = google_project.project.project_id
  role    = "roles/storage.admin"

  members = [
    "user:${data.google_client_openid_userinfo.me.email}",
  ]
}

resource "null_resource" "ar-redirect" {

  provisioner "local-exec" {
    command = <<-EOT
      curl -H 'Authorization: Bearer ${nonsensitive(data.google_client_config.default.access_token)}' \
      -H 'Content-type: application/json' \
      https://artifactregistry.googleapis.com/v1/projects/${google_project.project.project_id}/projectSettings?updateMask=legacyRedirectionState \
      -X PATCH \
      --data '{
        "legacyRedirectionState": "REDIRECTION_FROM_GCR_IO_ENABLED"
      }'
    EOT
  }
  depends_on = [
    google_project_iam_binding.storageAdmin
  ]
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
  repository_url        = "${google_artifact_registry_repository.gcb1_repo.location}-docker.pkg.dev/${google_project.project.project_id}/${google_artifact_registry_repository.gcb1_repo.repository_id}"
  legacy_repository_url = "${google_artifact_registry_repository.legacy.repository_id}/${google_project.project.project_id}"
}

output "artifact_registry" {
  value = google_artifact_registry_repository.gcb1_repo.id
}

output "legacy_artifact_registry" {
  value = google_artifact_registry_repository.legacy.repository_id
}
