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

# Also include a small GKE cluster to test GKE node detection.
resource "google_container_cluster" "gke1" {
  provider           = google
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke1"
  location           = "europe-west1-b"
  initial_node_count = 4
  node_config {
    machine_type = "e2-small"
  }
  resource_labels = {
    gcp_doctor_test = "gke"
  }
}
