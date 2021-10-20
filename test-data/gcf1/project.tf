terraform {
  backend "gcs" {
    bucket = "gcpd-gcf1-s6ew-tfstate"
  }
}

provider "google" {
  project = "gcpd-gcf1-s6ew"
}

provider "google-beta" {
  project = "gcpd-gcf1-s6ew"
}

resource "google_project_service" "cloudfunctions" {
  project = "gcpd-gcf1-s6ew"
  service = "cloudfunctions.googleapis.com"
}

resource "google_project_service" "cloudresourcemanager" {
  project = "gcpd-gcf1-s6ew"
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_project_service" "cloudbuild" {
  project = "gcpd-gcf1-s6ew"
  service = "cloudbuild.googleapis.com"
}

output "project_id" {
  value = "gcpd-gcf1-s6ew"
}
