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

resource "google_compute_instance_template" "default" {
  project      = google_project.project.project_id
  depends_on   = [google_project_service.compute]
  name         = "mig-template"
  machine_type = "e2-micro"
  disk {
    source_image = "debian-cloud/debian-11"
    auto_delete  = true
    boot         = true
  }
  network_interface {
    network = "default"
  }
}

resource "google_compute_instance_group_manager" "mig" {
  project            = google_project.project.project_id
  depends_on         = [google_project_service.compute]
  name               = "mig"
  base_instance_name = "mig"
  zone               = "europe-west4-a"
  version {
    instance_template = google_compute_instance_template.default.id
  }
  target_size = 2
}
