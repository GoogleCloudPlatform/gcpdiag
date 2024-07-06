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
  machine_type   = "e2-standard-2"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["faulty-ssh-instance", "gce-secured-instance-test-deny"]
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
  # Throw some errors to Serial console logs
  echo "blocked for more than 20 seconds" > /dev/console
  echo "Corruption of in-memory data detected. Shutting down filesystem" > /dev/console
  echo "Memory cgroup out of memory" >> /dev/console
  echo "No space left on device" >  /dev/console

  apt install stress-ng -y

  stress-ng --cpu 4 --vm 4 --vm-bytes 4G --io 5 --hdd 14--timeout 60m &

  while true; do
    : # Do nothing, which consumes CPU cycles
  done

  EOT
}

# Fault windows

resource "google_compute_instance" "faulty_windows_ssh" {
  project        = google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "faulty-windows-ssh"
  machine_type   = "e2-standard-2"
  zone           = "europe-west2-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  tags = ["faulty-ssh-instance", "gce-secured-instance-test-deny"]
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
  metadata_startup_script = <<-EOT
  #!/bin/bash
  echo "disk is at or near capacity" > /dev/console
  echo "The IO operation at logical block address 0x... for Disk 0 (PDO name: \Device\...) was retried"  > /dev/console
  EOT
}
