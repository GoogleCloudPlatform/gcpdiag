resource "google_sourcerepo_repository" "test-repo" {
  name       = "test-repo"
  project    = google_project.project.project_id
  depends_on = [google_project_service.sourcerepo]
}
