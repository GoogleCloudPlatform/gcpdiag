resource "google_service_account" "service_account_custom1" {
  account_id   = "gcb-custom1"
  display_name = "Custom Service Account 1"
  project      = google_project.project.project_id
}

resource "google_service_account" "service_account_custom2" {
  account_id   = "gcb-custom2"
  display_name = "Custom Service Account 2"
  project      = google_project.project.project_id
}

output "service_account_custom1_email" {
  value = google_service_account.service_account_custom1.email
}
