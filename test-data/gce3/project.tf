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

provider "google" {
  project = var.project_id
}

resource "random_string" "project_id_suffix" {
  length  = 8
  lower   = true
  upper   = false
  special = false
}

resource "google_project_service" "compute" {
  project = data.google_project.project.project_id
  service = "compute.googleapis.com"
}

resource "google_project_service" "logging" {
  project = data.google_project.project.project_id
  service = "logging.googleapis.com"
}

resource "google_project_service" "monitoring" {
  project = data.google_project.project.project_id
  service = "monitoring.googleapis.com"
}

resource "google_project_service" "osconfig" {
  project = data.google_project.project.project_id
  service = "osconfig.googleapis.com"
}

resource "google_compute_project_metadata_item" "serial_logging" {
  project    = data.google_project.project.project_id
  depends_on = [google_project_service.compute]
  key        = "serial-port-logging-enable"
  value      = "true"
}

data "google_project" "project" {
  project_id = var.project_id
}

data "google_compute_image" "debian" {
  family  = "debian-11"
  project = "debian-cloud"
}

data "google_compute_default_service_account" "default" {
  project    = data.google_project.project.project_id
  depends_on = [google_project_service.compute]
}

resource "google_service_account" "no_log_metric_perm_service_account" {
  account_id   = "no-logging-monitoring-perm"
  project      = data.google_project.project.project_id
  display_name = "Service Account without monitoring or logging permissions"
}


output "project_id" {
  value = data.google_project.project.project_id
}

output "project_id_suffix" {
  value = random_string.project_id_suffix.id
}

output "project_nr" {
  value = data.google_project.project.number
}

output "org_id" {
  value = var.org_id
}

/**
module "agent_policy" {
  source  = "terraform-google-modules/cloud-operations/google//modules/agent-policy"
  version = "~> 0.2.4"

  project_id = data.google_project.project.project_id
  policy_id  = "ops-agents-example-policy"
  agent_rules = [
    {
      type               = "logging"
      version            = "current-major"
      package_state      = "installed"
      enable_autoupgrade = true
    },
    {
      type               = "metrics"
      version            = "current-major"
      package_state      = "installed"
      enable_autoupgrade = true
    },
  ]
  group_labels = [
    {
      env = "valid"
    }
  ]
  os_types = [
    {
      short_name = "debian"
      version    = "11"
    },
  ]
}
**/
