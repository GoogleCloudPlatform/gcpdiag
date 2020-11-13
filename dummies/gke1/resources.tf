resource "google_project_service" "container" {
  project = google_project.project.project_id
  service = "container.googleapis.com"
}

resource "google_container_cluster" "gke1" {
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke1"
  location           = "europe-west4-a"
  initial_node_count = 1
  resource_labels = {
    foo = "bar"
  }
}

resource "google_container_cluster" "gke2" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke2"
  location           = "europe-west1"
  initial_node_count = 1
  cluster_telemetry {
    type = "DISABLED"
  }
}
