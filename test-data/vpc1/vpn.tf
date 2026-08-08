# Terraform configuration for VPN resources in vpc1.

data "google_compute_network" "default" {
  name       = "default"
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
}

resource "google_compute_vpn_gateway" "classic_vpn_gw1" {
  name    = "classic-vpn-gw1"
  network = data.google_compute_network.default.id
  region  = "us-central1"
  project = google_project.project.project_id
}
