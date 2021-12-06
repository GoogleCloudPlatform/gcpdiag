resource "google_container_cluster" "gke4" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke4"
  location           = "europe-west4-a"
  initial_node_count = 1
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "10.0.1.0/28"
  }
}
