# use this project to maintain terraform state

resource "google_project" "project" {
  name = "gcp-doctor test - terraform"
  # note: we add a "random" 2-byte suffix to make it easy to recreate the
  # project under another name and avoid project name conflicts.
  project_id      = "gcpd-terraform"
  org_id          = "98915863894"
  billing_account = "0072A3-8FBEBA-7CD837"
  skip_delete     = true
}

resource "google_storage_bucket" "gcpd-tf-state" {
  project                     = google_project.project.project_id
  name                        = "gcpd-tf-state"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = true
}
