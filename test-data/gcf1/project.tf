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
