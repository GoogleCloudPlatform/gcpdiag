resource "google_container_cluster" "gke4" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke4"
  location           = "europe-west4-a"
  initial_node_count = 1
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = "/14"
    services_ipv4_cidr_block = "/20"
  }
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "10.0.1.0/28"
  }
  workload_identity_config {
    workload_pool = "${google_project.project.project_id}.svc.id.goog"
  }
}

# configure cloud nat

data "google_compute_network" "default" {
  name    = "default"
  project = google_project.project.project_id
}

data "google_compute_subnetwork" "default" {
  name    = "default"
  project = google_project.project.project_id
  region  = "europe-west4"
}

resource "google_compute_router" "router" {
  name    = "gke-default-router"
  project = google_project.project.project_id
  region  = "europe-west4"
  network = data.google_compute_network.default.id
}

resource "google_compute_router_nat" "nat" {
  name                   = "gke-default-router-nat"
  project                = google_project.project.project_id
  router                 = google_compute_router.router.name
  region                 = google_compute_router.router.region
  nat_ip_allocate_option = "AUTO_ONLY"

  # source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = data.google_compute_subnetwork.default.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}
