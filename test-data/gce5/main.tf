/**
 * Copyright 2025 Google LLC
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

resource "google_project_iam_custom_role" "start_stop" {
  role_id     = "instanceScheduler"
  title       = "Instance Scheduler"
  description = "Minimum permissions required for Compute Engine System service account to be able to start/stop instances"
  permissions = ["compute.instances.start", "compute.instances.stop"]
  project     = google_project.project.project_id

}

resource "google_project_iam_member" "member" {
  project = google_project.project.project_id
  role    = google_project_iam_custom_role.start_stop.name
  member  = "serviceAccount:service-${google_project.project.number}@compute-system.iam.gserviceaccount.com"
}

data "google_compute_resource_policy" "hourly_startup" {
  name    = "gce-policy"
  region  = var.region
  project = google_project.project.project_id
}

data "google_compute_resource_policy" "hourly_startup_and_stop" {
  name    = "gce-policy-stop-and-start"
  region  = var.region
  project = google_project.project.project_id
}

resource "google_compute_resource_policy" "hourly_startup" {
  count = length(data.google_compute_resource_policy.hourly_startup) == 0 ? 1 : 0

  name        = "gce-policy"
  region      = var.region
  description = "Only Start instances"
  instance_schedule_policy {
    vm_start_schedule {
      schedule = "0 * * * *"
    }
    time_zone = "US/Central"
  }
  project = google_project.project.project_id
}

resource "google_compute_resource_policy" "hourly_startup_and_stop" {
  count       = length(data.google_compute_resource_policy.hourly_startup_and_stop) == 0 ? 1 : 0
  name        = "gce-policy-stop-and-start"
  region      = var.region
  description = "Start and stop instances"
  instance_schedule_policy {
    vm_start_schedule {
      schedule = "0 * * * *"
    }
    vm_stop_schedule {
      schedule = "5 * * * *"
    }
    time_zone = "US/Central"
  }
  project = google_project.project.project_id
}

resource "google_compute_instance" "vm_instance" {
  name         = "start-and-stop-vm"
  machine_type = "f1-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    # A default network is created for all GCP projects
    network = "default"
    access_config {
    }
  }
  project           = google_project.project.project_id
  resource_policies = [data.google_compute_resource_policy.hourly_startup_and_stop.id]
}

resource "google_compute_instance" "spot_vm_instance" {
  name         = "spot-vm-termination"
  machine_type = "f1-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  scheduling {
    preemptible                 = true
    automatic_restart           = false
    provisioning_model          = "SPOT"
    instance_termination_action = "STOP"
  }

  network_interface {
    # A default network is created for all GCP projects
    network = "default"
    access_config {
    }
  }
  project           = google_project.project.project_id
  resource_policies = [data.google_compute_resource_policy.hourly_startup_and_stop.id]
}

resource "google_compute_instance" "shielded_vm_integrity_failure" {
  name         = "shielded-vm-integrity-failure"
  machine_type = "f1-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    # A default network is created for all GCP projects
    network = "default"
    access_config {
    }
  }
  project           = google_project.project.project_id
  resource_policies = [data.google_compute_resource_policy.hourly_startup.id]
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata_startup_script = <<-EOF
    #! /bin/bash
    apt-get upgrade -y
    update-grub
    reboot
  EOF
}

resource "google_compute_instance_template" "apache_template" {
  name           = "apache-instance-template"
  machine_type   = "e2-micro"
  can_ip_forward = false

  tags = ["apache-server"]

  disk {
    auto_delete  = true
    boot         = true
    source_image = "debian-cloud/debian-11"
  }

  network_interface {
    network = "default"
    access_config {}
  }
  project = google_project.project.project_id
}

resource "google_compute_health_check" "apache_health_check" {
  name                = "apache-health-check"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 2

  http_health_check {
    port = 80
  }
  project = google_project.project.project_id
}

resource "google_compute_instance_group_manager" "apache_mig" {
  name               = "apache-mig-timeout"
  base_instance_name = "apache-instance"
  version {
    instance_template = google_compute_instance_template.apache_template.id
  }
  target_size = 2

  auto_healing_policies {
    health_check      = google_compute_health_check.apache_health_check.id
    initial_delay_sec = 300
  }
  project = google_project.project.project_id
  zone    = var.zone

}
