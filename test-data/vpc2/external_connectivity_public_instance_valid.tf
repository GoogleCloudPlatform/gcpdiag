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


resource "google_compute_instance" "public-linux-valid" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "public-linux-valid"
  machine_type   = "f1-micro"
  zone           = var.zone
  desired_status = "RUNNING"
  network_interface {
    network    = "default"
    subnetwork = google_compute_subnetwork.public_subnet.id
    access_config {}
  }
  tags = ["valid-vpc-instance"]
  scheduling {
    preemptible       = true
    automatic_restart = false
  }

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11" # Choose an image
    }
  }

  labels = {
    foo = "bar"
  }

}

# firewall configuration used for connectivity testing
resource "google_compute_firewall" "public-linux-egress-allow" {
  name    = "public-linux-egress-allow"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  direction = "EGRESS"

  allow {
    protocol = "all"
  }

  target_tags = google_compute_instance.public-linux-valid.tags
  depends_on  = [google_compute_instance.public-linux-valid]
}
