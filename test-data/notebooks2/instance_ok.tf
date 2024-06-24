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

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/workbench_instance

resource "google_workbench_instance" "notebooks2instance-ok" {
  project  = google_project.project.project_id
  name     = "notebooks2instance-ok"
  location = "us-west1-a"
  gce_setup {
    machine_type = "e2-standard-4"
    boot_disk {
      disk_size_gb = 150
      disk_type    = "PD_BALANCED"
    }
    data_disks {
      disk_size_gb = 100
      disk_type    = "PD_BALANCED"
    }
    vm_image {
      project = "cloud-notebooks-managed"
      family  = "workbench-instances"
    }
    metadata = {
      serial-port-logging-enable = true
      report-event-health        = true
      terraform                  = true
      report-dns-resolution      = true
      disable-mixer              = true
      idle-timeout-seconds       = 10800
    }
  }
  instance_owners      = []
  disable_proxy_access = false
  desired_state        = "ACTIVE"
}
