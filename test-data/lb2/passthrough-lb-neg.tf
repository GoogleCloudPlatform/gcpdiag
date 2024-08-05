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

# Passthrough load balancer with NEG backend

resource "google_compute_network_endpoint" "default-endpoint" {
  project                = google_project.project.project_id
  network_endpoint_group = google_compute_network_endpoint_group.neg1.name
  zone                   = "europe-west4-b"

  instance   = google_compute_instance.neg-vm.name
  ip_address = google_compute_instance.neg-vm.network_interface[0].network_ip
}

resource "google_compute_instance" "neg-vm" {
  project = google_project.project.project_id

  name           = "neg-vm"
  machine_type   = "e2-medium"
  zone           = "europe-west4-b"
  desired_status = "RUNNING"
  network_interface {
    subnetwork_project = google_project.project.project_id
    subnetwork         = "default"
  }

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      labels = {
        my_label = "value"
      }
    }
  }

  metadata_startup_script = "#! /bin/bash\n     sudo apt-get update\n     sudo apt-get install apache2 -y\n     sudo a2ensite default-ssl\n     sudo a2enmod ssl\n     sudo vm_hostname=\"$(curl -H \"Metadata-Flavor:Google\" \\\n   http://169.254.169.254/computeMetadata/v1/instance/name)\"\n   sudo echo \"Page served from: $vm_hostname\" | \\\n   tee /var/www/html/index.html\n   sudo systemctl restart apache2"
  depends_on              = [google_project_service.compute]
}

resource "google_compute_network_endpoint_group" "neg1" {
  project               = google_project.project.project_id
  name                  = "neg1"
  network               = "default"
  subnetwork            = "default"
  network_endpoint_type = "GCE_VM_IP"
  zone                  = "europe-west4-b"
  depends_on            = [google_project_service.compute]
}

resource "google_compute_firewall" "passthrough-lb-firewall" {
  project       = google_project.project.project_id
  depends_on    = [google_project_service.compute]
  name          = "fw-allow-passthrough-health-check"
  direction     = "INGRESS"
  network       = "default"
  priority      = 1000
  source_ranges = ["35.191.0.0/16", "209.85.152.0/22", "209.85.204.0/22"]
  target_tags   = ["allow-health-check"]
  allow {
    ports    = ["80"]
    protocol = "tcp"
  }
}

resource "google_compute_region_health_check" "tcp-basic-check-2" {
  depends_on = [google_project_service.compute]
  name       = "tcp-basic-check-2"
  project    = google_project.project.project_id
  region     = "europe-west4"

  check_interval_sec = 5
  timeout_sec        = 5

  tcp_health_check {
    port = 80
  }

  log_config {
    enable = true
  }
}

resource "google_compute_region_backend_service" "backend-service-2" {
  name                            = "backend-service-2"
  project                         = google_project.project.project_id
  region                          = "europe-west4"
  connection_draining_timeout_sec = 0
  health_checks                   = [google_compute_region_health_check.tcp-basic-check-2.id]
  load_balancing_scheme           = "EXTERNAL"
  protocol                        = "TCP"
  session_affinity                = "NONE"
  timeout_sec                     = 30
  backend {
    group          = google_compute_network_endpoint_group.neg1.id
    balancing_mode = "CONNECTION"
  }
}

resource "google_compute_forwarding_rule" "forwarding-rule-1" {
  project               = google_project.project.project_id
  name                  = "tcp-content-rule"
  region                = "europe-west4"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "80-80"
  backend_service       = google_compute_region_backend_service.backend-service-2.id
}
