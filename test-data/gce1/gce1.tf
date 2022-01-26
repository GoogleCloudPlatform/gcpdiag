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

resource "google_compute_instance" "gce1" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "gce1"
  machine_type   = "f1-micro"
  zone           = "europe-west4-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["secured-instance"]
  scheduling {
    preemptible       = true
    automatic_restart = false
  }
  boot_disk {
    initialize_params {
      image = data.google_compute_image.windows.self_link
    }
  }
  service_account {
    email = data.google_compute_default_service_account.default.email
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol"
    ]
  }
  labels = {
    foo = "bar"
  }
}

# firewall configuration used for connectivity testing

resource "google_compute_firewall" "secured_instance_test_deny" {
  name    = "gce-secured-instance-test-deny"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  deny {
    ports    = ["22", "3389"]
    protocol = "tcp"
  }

  source_ranges = ["0.0.0.0/0"]

  target_tags = google_compute_instance.gce1.tags

  depends_on = [google_compute_instance.gce1]
}
