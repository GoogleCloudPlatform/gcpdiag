resource "google_project" "project" {
  name = "gcp-doctor test - gke1"
  # note: we add a "random" 2-byte suffix to make it easy to recreate the
  # project under another name and avoid project name conflicts.
  project_id      = "gcpd-gke-1-9b90"
  org_id          = "98915863894"
  billing_account = "0072A3-8FBEBA-7CD837"
  skip_delete     = true
}

output "project_id" {
  value = google_project.project.project_id
}
