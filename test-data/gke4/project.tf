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

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0.3"
    }
    google = {
      source  = "hashicorp/google"
      version = ">= 4.4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 4.4.0"
    }
  }
}

resource "random_string" "project_id_suffix" {
  length  = 8
  lower   = true
  upper   = false
  special = false
}

resource "google_project" "project" {
  name       = "gcpdiag-gke4-runbook"
  project_id = "gcpdiag-gke4-${random_string.project_id_suffix.id}"
  org_id     = var.folder_id == "" ? var.org_id : null
  folder_id  = var.folder_id != "" ? var.folder_id : null
  labels = {
    gcpdiag : "test"
  }
  lifecycle {
    ignore_changes = all
  }
}

resource "google_project_service" "compute" {
  project = google_project.project.project_id
  service = "compute.googleapis.com"
}

resource "google_project_service" "container" {
  project = google_project.project.project_id
  service = "container.googleapis.com"

  depends_on = [google_project_service.compute]
}

resource "google_project_service" "cloudresourcemanager" {
  project = google_project.project.project_id
  service = "cloudresourcemanager.googleapis.com"
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
