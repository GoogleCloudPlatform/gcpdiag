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

resource "google_compute_instance" "valid_linux_ssh" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "valid-linux-ssh"
  machine_type   = "f1-micro"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["valid-ssh-instance"]
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
  metadata = {
    enable-oslogin = true
  }
  metadata_startup_script = <<-EOT
  #!/bin/bash

  curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
  sudo bash add-google-cloud-ops-agent-repo.sh --also-install
  EOT
}

# Fault windows running ssh

resource "google_compute_instance" "valid_windows_ssh" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "valid-windows-ssh"
  machine_type   = "f1-micro"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["valid-ssh-instance"]
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
    enable-oslogin = true
  }
}

# firewall configuration used for connectivity testing

resource "google_compute_firewall" "secured_instance_test_allow" {
  name    = "gce-secured-instance-test-allow"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  allow {
    ports    = ["22"]
    protocol = "tcp"
  }

  # allow external access and IAP
  source_ranges = [
    "0.0.0.0/0",
    "35.235.240.0/20"
  ]

  target_tags = google_compute_instance.faulty_linux_ssh.tags
  depends_on  = [google_compute_instance.faulty_linux_ssh]
}

resource "google_service_account" "canssh_service_account" {
  account_id   = "canssh"
  display_name = "Can SSH Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "service_account_member_policy" {
  for_each   = { for role in var.roles : role => role }
  project    = var.project_id
  role       = each.value
  member     = "serviceAccount:${google_service_account.canssh_service_account.name}"
  depends_on = [google_service_account.canssh_service_account]
}
