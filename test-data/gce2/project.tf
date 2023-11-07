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

resource "random_string" "project_id_suffix" {
  length  = 8
  number  = true
  lower   = true
  upper   = false
  special = false
}

resource "google_project" "project" {
  name       = "gcpdiag test - faultyssh"
  project_id = var.project_id != "" ? var.project_id : "gcpdiag-gce2-${random_string.project_id_suffix.id}"
  org_id     = var.folder_id == "" ? var.org_id : null
  folder_id  = var.folder_id != "" ? var.folder_id : null
  // billing_account = var.billing_account_id
  labels = {
    gcpdiag : "test"
  }
}

resource "google_project_service" "compute" {
  project = google_project.project.project_id
  service = "compute.googleapis.com"
}

resource "google_compute_project_metadata_item" "serial_logging" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  key        = "serial-port-logging-enable"
  value      = "true"
}

data "google_compute_default_service_account" "default" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
}

data "google_compute_image" "debian" {
  family  = "debian-11"
  project = "debian-cloud"
}

data "google_compute_image" "windows" {
  family  = "windows-2019-core"
  project = "windows-cloud"
}

output "project_id" {
  value = google_project.project.project_id
}

output "project_id_suffix" {
  value = random_string.project_id_suffix.id
}

output "project_nr" {
  value = google_project.project.number
}

output "org_id" {
  value = var.org_id
}
