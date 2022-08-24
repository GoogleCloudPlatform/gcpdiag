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

resource "google_data_fusion_instance" "datafusion1" {
  # https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/data_fusion_instance
  project                       = google_project.project.project_id
  name                          = "datafusion1"
  description                   = "gcpdiag Test Data Fusion instance"
  region                        = "us-central1"
  type                          = "BASIC"
  enable_stackdriver_logging    = true
  enable_stackdriver_monitoring = true
  labels = {
    gcpdiag = "test"
  }
  private_instance = true
  network_config {
    network       = "default"
    ip_allocation = "10.89.48.0/22"
  }
}
