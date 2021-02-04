# GKE cluster with monitoring disabled
resource "google_container_cluster" "gke1" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke1"
  location           = "europe-west4-a"
  initial_node_count = 1
  cluster_telemetry {
    type = "DISABLED"
  }
  resource_labels = {
    foo = "bar"
  }
}
