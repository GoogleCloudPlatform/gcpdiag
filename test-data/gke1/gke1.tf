/**
 * Copyright 2021 Google LLC
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

# GKE cluster with monitoring disabled
# And with small pod CIDR

resource "google_service_account" "gke1_sa" {
  project      = google_project.project.project_id
  account_id   = "gke1sa"
  display_name = "GKE 1 Service Account"
}

resource "google_compute_subnetwork" "secondary_ip_range_pod" {
  project       = google_project.project.project_id
  depends_on    = [google_project_service.compute]
  network       = "default"
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

resource "google_compute_subnetwork_iam_member" "gke1_subnet" {
  project    = google_compute_subnetwork.secondary_ip_range_pod.project
  region     = google_compute_subnetwork.secondary_ip_range_pod.region
  subnetwork = google_compute_subnetwork.secondary_ip_range_pod.name
  role       = "roles/compute.networkUser"
  member     = "serviceAccount:${google_service_account.gke1_sa.email}"
}

resource "google_container_cluster" "gke1" {
  provider   = google-beta
  project    = google_project.project.project_id
  depends_on = [google_project_service.container]
  name       = "gke1"
  subnetwork = google_compute_subnetwork.secondary_ip_range_pod.name
  location   = "europe-west4-a"
  release_channel {
    channel = "UNSPECIFIED"
  }
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
