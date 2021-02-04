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
    "stackdriver.resourceMetadata.write"
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

# GKE cluster with monitoring enabled and service account using a custom role
resource "google_container_cluster" "gke2" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke2"
  location           = "europe-west1"
  initial_node_count = 1
  node_config {
    service_account = google_service_account.gke2_sa.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}
