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

# This custom role is used to test iam.py's code that deals
# with verifying permissions including custom roles.
resource "google_project_iam_custom_role" "gke2_custom_role" {
  project     = google_project.project.project_id
  role_id     = "gke2_custom_role"
  title       = "GKE Custom Role"
  description = "A description"
  permissions = [
    # monitoring.viewer
    "cloudnotifications.activities.list",
    "monitoring.alertPolicies.get",
    "monitoring.alertPolicies.list",
    "monitoring.dashboards.get",
    "monitoring.dashboards.list",
    "monitoring.groups.get",
    "monitoring.groups.list",
    "monitoring.metricDescriptors.get",
    "monitoring.metricDescriptors.list",
    "monitoring.monitoredResourceDescriptors.get",
    "monitoring.monitoredResourceDescriptors.list",
    "monitoring.notificationChannelDescriptors.get",
    "monitoring.notificationChannelDescriptors.list",
    "monitoring.notificationChannels.get",
    "monitoring.notificationChannels.list",
    "monitoring.publicWidgets.get",
    "monitoring.publicWidgets.list",
    "monitoring.services.get",
    "monitoring.services.list",
    "monitoring.slos.get",
    "monitoring.slos.list",
    "monitoring.timeSeries.list",
    "monitoring.uptimeCheckConfigs.get",
    "monitoring.uptimeCheckConfigs.list",
    # only for org-level:
    #"resourcemanager.projects.get",
    #"resourcemanager.projects.list",

    # monitoring.metricWriter
    "monitoring.metricDescriptors.create",
    "monitoring.metricDescriptors.get",
    "monitoring.metricDescriptors.list",
    "monitoring.monitoredResourceDescriptors.get",
    "monitoring.monitoredResourceDescriptors.list",
    "monitoring.timeSeries.create",

    #"logging.logWriter",
    "logging.logEntries.create",

    #"stackdriver.resourceMetadata.writer"
    "stackdriver.resourceMetadata.write",
    "opsconfigmonitoring.resourceMetadata.list",

    # container.nodeServiceAgent
    "autoscaling.sites.writeMetrics",
    "logging.logEntries.create",
    "monitoring.metricDescriptors.create",
    "monitoring.metricDescriptors.list",
    "monitoring.timeSeries.create",
    #"resourcemanager.projects.get",
    #"resourcemanager.projects.list",
    "storage.objects.get",
    "storage.objects.list",
  ]
}

resource "google_service_account" "gke2_sa" {
  project      = google_project.project.project_id
  account_id   = "gke2sa"
  display_name = "GKE Service Account"
}


resource "google_project_iam_member" "gke2_sa" {
  project = google_project.project.project_id
  role    = google_project_iam_custom_role.gke2_custom_role.name
  member  = "serviceAccount:${google_service_account.gke2_sa.email}"
}

resource "google_service_account_iam_member" "gke2_sa" {
  service_account_id = google_service_account.gke2_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.gke2_sa.email}"
}

# GKE cluster with monitoring enabled and service account using a custom role
resource "google_container_cluster" "gke2" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke2"
  location           = "europe-west4"
  initial_node_count = 1
  release_channel {
    channel = "UNSPECIFIED"
  }
  cluster_telemetry {
    type = "SYSTEM_ONLY"
  }
  node_config {
    service_account = google_service_account.gke2_sa.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    tags = ["gke-gke2-custom-tag"]
  }
  workload_identity_config {
    workload_pool = "${google_project.project.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "low_pod_per_node_pool" {
  name              = "low-pod-per-node-pool"
  project           = google_project.project.project_id
  cluster           = google_container_cluster.gke2.id
  node_count        = 1
  max_pods_per_node = 8

  node_config {
    preemptible = true
  }
}

# firewall configuration used for connectivity testing

resource "google_compute_firewall" "vms_test_deny" {
  name    = "gke-gke2-vms-test-deny"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  deny {
    ports    = ["1-1000"]
    protocol = "udp"
  }

  source_ranges = ["10.128.0.0/9"]

  target_tags = google_container_cluster.gke2.node_config[0].tags

  depends_on = [google_container_cluster.gke2]
}

resource "google_compute_firewall" "all_test_deny" {
  name    = "gke-gke2-all-test-deny"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  deny {
    ports    = ["1-1000"]
    protocol = "tcp"
  }

  source_ranges = ["10.0.0.0/8"]

  target_tags = google_container_cluster.gke2.node_config[0].tags

  depends_on = [google_container_cluster.gke2]
}

output "gke2_sa" {
  value = google_service_account.gke2_sa.name
}
