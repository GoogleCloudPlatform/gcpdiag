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

resource "google_service_account" "no_compute_service_account" {
  account_id   = "no-compute-perm-sa"
  display_name = "Service Account without compute permissions"
  project      = google_project.project.project_id
}

resource "google_service_account" "compute_service_account" {
  account_id   = "compute-sa"
  display_name = "Service Account without compute permissions"
  project      = google_project.project.project_id
}


resource "google_project_iam_binding" "compute_instance_admin_binding" {
  project = google_project.project.project_id
  role    = "roles/compute.instanceAdmin"

  members = [
    "serviceAccount:${google_service_account.compute_service_account.email}"
  ]
}

resource "google_compute_instance" "existing_instance" {
  name         = "existing-instance"
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
  project = google_project.project.project_id
  service_account {
    email  = google_service_account.no_compute_service_account.email
    scopes = ["cloud-platform"]
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata_startup_script = <<-EOF
    # Fetch instance name and zone from metadata server
    INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" -s http://metadata.google.internal/computeMetadata/v1/instance/name)
    ZONE=$(curl -H "Metadata-Flavor: Google" -s http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F'/' '{print $NF}')

    # create another instance with the same VM details
    echo "0 * * * * gcloud compute instances create $INSTANCE_NAME --zone=$ZONE" | crontab -
  EOF
}

resource "google_compute_instance" "gpu_instance_creator" {
  name         = "gpu-instance-creator"
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
  project = google_project.project.project_id
  service_account {
    email  = google_service_account.compute_service_account.email
    scopes = ["cloud-platform"]
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata_startup_script = <<-EOF
    # Fetch instance name and zone from metadata server
    INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" -s http://metadata.google.internal/computeMetadata/v1/instance/name)
    ZONE=$(curl -H "Metadata-Flavor: Google" -s http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F'/' '{print $NF}')
    PROJECT_NUMBER=$(curl -H "Metadata-Flavor: Google" -s http://metadata.google.internal/computeMetadata/v1/project/numeric-project-id)
    # with a gpu
    echo "0 * * * * gcloud compute instances create non-existing-gpu-instance --machine-type=a3-megagpu-8g --zone=$ZONE --accelerator=type=nvidia-h100-mega-80gb,count=1 --maintenance-policy=TERMINATE --no-restart-on-failure" | crontab -
    # with a service account
    echo "0 * * * * gcloud compute instances create no-service-account-user-permission  --zone=$ZONE  --service-account=service-$PROJECT_NUMBER@compute-system.iam.gserviceaccount.com" | crontab -
  EOF
}
resource "google_compute_instance_template" "apache_template" {
  name           = "apache-instance-template"
  machine_type   = "e2-micro"
  can_ip_forward = false

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
