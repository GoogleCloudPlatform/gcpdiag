# public autopilot cluster
resource "google_container_cluster" "autopilot-gke1" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "autopilot-gke1"
  location           = "europe-west4"
  initial_node_count = 1
  enable_autopilot   = true

  # https://github.com/hashicorp/terraform-provider-google/issues/10782
  ip_allocation_policy {}
}

# private autopilot cluster
resource "google_container_cluster" "autopilot-gke2" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "autopilot-gke2"
  location           = "europe-west4"
  initial_node_count = 1
  enable_autopilot   = true
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = "/17"
    services_ipv4_cidr_block = "/22"
  }
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.114.128/28"
  }
}
