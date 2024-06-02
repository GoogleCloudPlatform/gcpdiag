/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


# Public Subnet
resource "google_compute_subnetwork" "public_subnet" {
  name          = "public-subnet"
  project       = google_project.project.project_id
  network       = "default"
  ip_cidr_range = "10.0.0.0/24" # Adjust as needed
  region        = var.region
}

# Private Subnet
resource "google_compute_subnetwork" "private_subnet" {
  name          = "private-subnet"
  project       = google_project.project.project_id
  network       = "default"
  ip_cidr_range = "10.10.0.0/24" # Adjust as needed
  region        = var.region
}



# Cloud Router
resource "google_compute_router" "nat_router" {
  name    = "nat-router"
  region  = var.region
  network = "default"
  project = google_project.project.project_id
}

# Cloud NAT Gateway
resource "google_compute_router_nat" "nat_gateway" {
  name                               = "nat-gateway"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY" # Allocate ephemeral IP automatically
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  project                            = google_project.project.project_id

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
