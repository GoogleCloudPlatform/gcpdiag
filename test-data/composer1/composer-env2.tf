resource "google_service_account" "env2_sa" {
  project      = google_project.project.project_id
  account_id   = "env2sa"
  display_name = "Composer Environment 2 Service Account"
}

resource "google_project_iam_member" "env2_sa" {
  project = google_project.project.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.env2_sa.email}"
}

resource "google_composer_environment" "env2" {
  name    = "env2"
  region  = "us-central1"
  project = google_project.project.project_id

  config {
    node_config {
      service_account = google_service_account.env2_sa.name

      ip_allocation_policy {
        use_ip_aliases = true
      }
    }

    private_environment_config {
      enable_private_endpoint = true
    }
  }

  depends_on = [google_project_service.composer]
}
