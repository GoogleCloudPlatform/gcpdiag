resource "google_compute_network" "private_network" {
  project                 = google_project.project.project_id
  name                    = "private-network"
  auto_create_subnetworks = "false"
}

resource "google_compute_global_address" "private_ip_address" {
  project       = google_project.project.project_id
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 20
  network       = google_compute_network.private_network.id
  address       = "172.17.0.0"

  depends_on = [google_project_service.compute,
  google_compute_network.private_network]

}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.private_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]

  depends_on = [google_project_service.servicenetworking,
  google_compute_global_address.private_ip_address]
}

resource "google_sql_database_instance" "sql1" {
  project          = google_project.project.project_id
  name             = "sql1"
  region           = "us-central1"
  database_version = "MYSQL_8_0"

  depends_on = [google_project_service.sqladmin,
  google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

provider "google-beta" {
  region = "us-central1"
  zone   = "us-central1-a"
}
