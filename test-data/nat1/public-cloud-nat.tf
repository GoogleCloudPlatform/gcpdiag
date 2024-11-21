# 1. Create a VPC Network
resource "google_compute_network" "nat_vpc_network" {
  name                    = "nat-vpc-network"
  auto_create_subnetworks = false
  project                 = google_project.project.project_id
}

# 2. Create a Subnet in the VPC Network
resource "google_compute_subnetwork" "private_subnet" {
  name                     = "private-subnet"
  ip_cidr_range            = "172.16.1.0/24"
  region                   = "europe-west4"
  network                  = google_compute_network.nat_vpc_network.id
  private_ip_google_access = true
  project                  = google_project.project.project_id
}

# 3. Create 3 VM instances without external IP addresses
resource "google_compute_instance" "vm_instances" {
  count        = 4
  name         = "private-vm-${count.index}"
  machine_type = "e2-medium"
  zone         = "europe-west4-a"
  project      = google_project.project.project_id

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.private_subnet.id
    #access_config      = {} # No external IP by default
  }
}

# 4. Create a Cloud Router
resource "google_compute_router" "public_nat_cloud_router" {
  name    = "public-nat-cloud-router"
  network = google_compute_network.nat_vpc_network.name
  region  = "europe-west4"
  project = google_project.project.project_id
}

# 5. Create a Static IP Address for the NAT Gateway
resource "google_compute_address" "public_nat_ip_1" {
  name    = "public-nat-ip-1"
  region  = "europe-west4"
  project = google_project.project.project_id
}

# 6. Create a Cloud NAT Gateway with a Static IP and Custom Port Settings
resource "google_compute_router_nat" "public_nat_gateway" {
  name                               = "public-nat-gateway"
  router                             = google_compute_router.public_nat_cloud_router.name
  region                             = "europe-west4"
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = [google_compute_address.public_nat_ip_1.id]
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  project                            = google_project.project.project_id

  min_ports_per_vm               = 32000
  enable_dynamic_port_allocation = false

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
