resource "random_string" "project_id_suffix" {
  length  = 8
  number  = true
  lower   = true
  upper   = false
  special = false
}

resource "google_project" "project" {
  name            = "gcpdiag test - dataproc1"
  project_id      = "gcpdiag-dataproc1-${random_string.project_id_suffix.id}"
  org_id          = var.folder_id == "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account_id
  labels = {
    gcpdiag : "test"
  }
}


resource "google_project_service" "compute" {
  project = google_project.project.project_id
  service = "compute.googleapis.com"
}

resource "google_project_service" "dataproc" {
  project            = google_project.project.project_id
  service            = "dataproc.googleapis.com"
  disable_on_destroy = false
}

output "project_id" {
  value = google_project.project.project_id
}

output "project_id_suffix" {
  value = random_string.project_id_suffix.id
}

output "project_nr" {
  value = google_project.project.number
}

output "org_id" {
  value = var.org_id
}
