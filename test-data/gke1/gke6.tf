/**
 * Copyright 2022 Google LLC
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

# This is to test GKE with GPU.
resource "google_container_cluster" "gke6" {
  provider           = google
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke6"
  location           = "europe-west4-a"
  initial_node_count = 1

  node_config {
    machine_type = "n1-standard-2"
    guest_accelerator {
      type  = "nvidia-tesla-v100"
      count = 1
    }
  }

  maintenance_policy {
    recurring_window {
      start_time = "2023-02-01T09:00:00Z"
      end_time   = "2023-02-01T17:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    }
  }

  resource_labels = {
    gcpdiag_test = "gke"
  }
}
