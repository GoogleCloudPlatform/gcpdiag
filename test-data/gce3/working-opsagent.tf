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

resource "google_compute_instance" "working_opsagent" {
  project        = data.google_project.project.project_id
  depends_on     = [google_project_service.compute]
  name           = "working-opsagent"
  machine_type   = "e2-micro"
  zone           = "europe-west2-a"
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
    env = "valid"

  }
}

resource "google_project_iam_member" "service_account_member_policy" {
  for_each   = { for role in var.roles : role => role }
  project    = data.google_project.project.project_id
  role       = each.value
  member     = "serviceAccount:${data.google_compute_default_service_account.default.email}"
  depends_on = [data.google_compute_default_service_account.default]
}
