/**
 * Copyright 2024 Google LLC
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

resource "google_compute_network" "my_network" {
  project                 = google_project.project.project_id
  name                    = "wbi-test-default"
  description             = "VPC network"
  auto_create_subnetworks = false
  provider                = google-old
}

resource "google_compute_subnetwork" "my_subnetwork" {
  project       = google_project.project.project_id
  name          = "wbi-test-default"
  network       = google_compute_network.my_network.id
  region        = "us-west1"
  ip_cidr_range = "10.0.1.0/24"
  provider      = google-old
}
