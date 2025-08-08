/**
 * Copyright 2022 Google LLC
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
    google = {
      source  = "hashicorp/google"
      version = "= 3.46.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 4.50.0"
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
  name            = "gcpdiag test - pubsub1"
  project_id      = "gcpdiag-pubsub1-${random_string.project_id_suffix.id}"
  org_id          = var.folder_id == "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account_id
  labels = {
    gcpdiag : "test"
  }
}

resource "google_project_service" "pubsub" {
  project = google_project.project.project_id
  service = "pubsub.googleapis.com"
}

resource "google_project_service" "bigquery" {
  project = google_project.project.project_id
  service = "bigquery.googleapis.com"
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

output "topic" {
  value = google_pubsub_topic.pubsub1topic.name
}

output "subscription" {
  value = google_pubsub_subscription.pubsub1subscription.name
}

output "bqsubscription" {
  value = google_pubsub_subscription.pubsub1subscription2.name
}

output "gcs_subscription" {
  value = google_pubsub_subscription.pubsub1subscription3gcs.name
}

output "gcs_subscription_bucket_name" {
  value = google_storage_bucket.pubsub_gcs_subscription_bucket.name
}
