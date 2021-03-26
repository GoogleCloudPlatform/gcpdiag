terraform {
  backend "gcs" {
    bucket = "gcpd-tf-state"
    prefix = "projects/gce"
  }
}

resource "google_project" "project" {
  name = "gcp-doctor test - gce1"
  # note: we add a "random" 2-byte suffix to make it easy to recreate the
  # project under another name and avoid project name conflicts.
  project_id      = "gcpd-gce1-4exv"
  org_id          = "98915863894"
  billing_account = "0072A3-8FBEBA-7CD837"
  skip_delete     = true
}

resource "google_project_service" "compute" {
  project = google_project.project.project_id
  service = "compute.googleapis.com"
}

resource "google_project_service" "container" {
  project = google_project.project.project_id
  service = "container.googleapis.com"
}

data "google_compute_default_service_account" "default" {
  project = google_project.project.project_id
}

data "google_compute_image" "cos" {
  family  = "cos-85-lts"
  project = "cos-cloud"
}


output "project_id" {
  value = google_project.project.project_id
}
