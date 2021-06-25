# Also include a small GKE cluster to test GKE node detection.
resource "google_container_cluster" "gke1" {
  provider           = google
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke1"
  location           = "europe-west1-b"
  initial_node_count = 4
  node_config {
    machine_type = "e2-small"
  }
  resource_labels = {
    gcp_doctor_test = "gke"
  }
}
