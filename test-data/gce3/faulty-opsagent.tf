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

resource "google_compute_instance" "faulty_opsagent" {
  project        = data.google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "faulty-opsagent"
  machine_type   = "e2-micro"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  scheduling {
    preemptible       = true
    automatic_restart = false
  }
  boot_disk {
    initialize_params {
      image = data.google_compute_image.debian.self_link
    }
  }
  service_account {
    email = google_service_account.no_log_metric_perm_service_account.email
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
    ]
  }
  metadata = {
    serial-port-logging-enable = "false"
  }
}

resource "google_compute_instance" "faulty_opsagent_no_sa" {
  project        = data.google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "faulty-opsagent-no-sa"
  machine_type   = "e2-micro"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  scheduling {
    preemptible       = true
    automatic_restart = false
  }
  boot_disk {
    initialize_params {
      image = data.google_compute_image.debian.self_link
    }
  }
  service_account {
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
    ]
  }
  metadata = {
    serial-port-logging-enable = "false"
  }
}
