
resource "google_compute_network" "test-bad-network" {
  name                    = "test-bad-network"
  description             = "VPC network without Dataproc specific firewall rules"
  auto_create_subnetworks = false
  project                 = google_project.project.project_id
}
resource "google_compute_subnetwork" "test-bad-subnet" {
  name          = "test-bad-subnet"
  ip_cidr_range = "10.128.0.0/20"
  region        = "us-central1"
  network       = google_compute_network.test-bad-network.id
  project       = google_project.project.project_id
}

resource "google_compute_firewall" "deny-icmp" {
  name    = "deny-icmp"
  network = google_compute_network.test-bad-network.name
  project = google_project.project.project_id
  deny {
    protocol = "icmp"
  }
  source_tags = ["icmp-deny"]
}
