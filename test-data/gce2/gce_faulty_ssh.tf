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

resource "google_compute_instance" "faulty_linux_ssh" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "faulty-linux-ssh"
  machine_type   = "f1-micro"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["faulty-ssh-instance"]
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
  metadata_startup_script = <<-EOT
  #!/bin/bash

  while true; do
    : # Do nothing, which consumes CPU cycles
  done
  EOT
  metadata = {
    enable-oslogin = false
  }
}

# Fault windows running ssh

resource "google_compute_instance" "faulty_windows_ssh" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "faulty-windows-ssh"
  machine_type   = "f1-micro"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["faulty-ssh-instance"]
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
  metadata = {
    enable-oslogin = false
  }
}

# firewall configuration used for connectivity testing

resource "google_compute_firewall" "secured_instance_test_deny" {
  name    = "gce-secured-instance-test-deny"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  deny {
    ports    = ["22"]
    protocol = "tcp"
  }

  source_ranges = [
    "0.0.0.0/0",      # Block external access
    "35.235.240.0/20" # block IAP
  ]

  target_tags = google_compute_instance.faulty_linux_ssh.tags
  depends_on  = [google_compute_instance.faulty_linux_ssh]
}

resource "google_service_account" "service_account" {
  account_id   = "cannotssh"
  display_name = "Cannot SSH Service Account"
  project      = google_project.project.number
}


resource "google_compute_project_metadata" "dummy_key" {
  metadata = {
    ssh-keys = <<EOF
      dev:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILg6UtHDNyMNAh0GjaytsJdrUxjtLy3APXqZfNZhvCeT dev
      foo:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILg6UtHDNyMNAh0GjaytsJdrUxjtLy3APXqZfNZhvCeT bar
    EOF
  }
}
