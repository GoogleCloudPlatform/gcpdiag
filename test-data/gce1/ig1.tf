resource "google_compute_instance_group" "instance_group_1" {
  project = google_project.project.project_id
  name    = "instance-group-1"

  instances = [
    google_compute_instance.gce1.id,
  ]

  named_port {
    name = "http"
    port = "8080"
  }

  named_port {
    name = "http"
    port = "8443"
  }

  zone       = "europe-west4-a"
  depends_on = [google_project_service.compute]
}

resource "google_compute_instance_group" "instance_group_2" {
  project = google_project.project.project_id
  name    = "instance-group-2"

  instances = [
    google_compute_instance.gce2.id,
  ]

  named_port {
    name = "http"
    port = "8080"
  }

  named_port {
    name = "https"
    port = "8443"
  }

  zone       = "europe-west4-a"
  depends_on = [google_project_service.compute]
}
