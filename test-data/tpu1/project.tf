resource "random_string" "project_id" {
  length  = 8
  number  = true
  lower   = true
  upper   = false
  special = false
}

resource "google_project" "project" {
  name            = "gcpdiag test - tpu1"
  project_id      = "gcpdiag-tpu1-${random_string.project_id.id}"
  org_id          = var.folder_id == "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account_id
}

resource "google_project_service" "tpu" {
  project = google_project.project.project_id
  service = "tpu.googleapis.com"
}

resource "google_project_service" "logging" {
  project = google_project.project.project_id
  service = "logging.googleapis.com"
}

output "project_id" {
  value = google_project.project.project_id
}

output "project_id_suffix" {
  value = random_string.project_id.id
}

output "project_nr" {
  value = google_project.project.number
}

output "org_id" {
  value = var.org_id
}
