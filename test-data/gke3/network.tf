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
  ip_cidr_range = "10.0.0.0/29" # Adjust as needed
  region        = var.region
}

resource "google_compute_subnetwork" "public_subnet-2" {
  name          = "public-subnet-2"
  project       = google_project.project.project_id
  network       = "default"
  ip_cidr_range = "10.10.0.0/24" # Adjust as needed
  region        = var.region
}
