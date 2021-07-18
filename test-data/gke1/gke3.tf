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

# Another custom role with just a few permissions
resource "google_project_iam_custom_role" "gke3_custom_role" {
  project     = google_project.project.project_id
  role_id     = "gke3_custom_role"
  title       = "GKE 3 Custom Role"
  description = "A description"
  permissions = [
    # monitoring.viewer
    "cloudnotifications.activities.list",
  ]
}

resource "google_service_account" "gke3_sa" {
  project      = google_project.project.project_id
  account_id   = "gke3sa"
  display_name = "GKE 3 Service Account"
}


resource "google_project_iam_member" "gke3_sa" {
  project = google_project.project.project_id
  role    = google_project_iam_custom_role.gke3_custom_role.name
  member  = "serviceAccount:${google_service_account.gke3_sa.email}"
}

resource "google_container_cluster" "gke3" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke3"
  location           = "europe-west1"
  initial_node_count = 1
  node_config {
    service_account = google_service_account.gke3_sa.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}
