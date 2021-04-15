# GKE cluster with monitoring disabled
# And with small pod CIDR

resource "google_compute_subnetwork" "secondary_ip_range_pod" {
  network       = "default"
  project       = google_project.project.project_id
  name          = "gke1-subnet"
  ip_cidr_range = "192.168.0.0/24"
  region        = "europe-west4"
  secondary_ip_range {
    range_name    = "gke1-secondary-range-pod"
    ip_cidr_range = "192.168.1.0/24"
  }
  secondary_ip_range {
    range_name    = "gke1-secondary-range-svc"
    ip_cidr_range = "192.168.2.0/24"
  }
}

resource "google_container_cluster" "gke1" {
  provider   = google-beta
  project    = google_project.project.project_id
  depends_on = [google_project_service.container]
  name       = "gke1"
  subnetwork = google_compute_subnetwork.secondary_ip_range_pod.name
  location   = "europe-west4-a"
  ip_allocation_policy {
    cluster_secondary_range_name  = "gke1-secondary-range-pod"
    services_secondary_range_name = "gke1-secondary-range-svc"
  }
  initial_node_count = 1
  cluster_telemetry {
    type = "DISABLED"
  }
  resource_labels = {
    foo = "bar"
  }
}
