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

# Create the GKE cluster
resource "google_container_cluster" "primary" {
  project            = google_project.project.project_id
  name               = "cluster-1"
  location           = var.zone
  initial_node_count = 4

  # Standard Cluster Configuration (default)
  remove_default_node_pool = true

  # Network Policy
  network_policy {
    enabled = true
  }

  network    = "default"
  subnetwork = google_compute_subnetwork.public_subnet.name
}

# Create the node pool
resource "google_container_node_pool" "primary_pool" {
  project    = google_project.project.project_id
  name       = "primary-node-pool"
  cluster    = google_container_cluster.primary.name
  location   = var.zone
  node_count = 4 # Initial node count

  # Node Configuration
  max_pods_per_node = 110

  # Node Management
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
