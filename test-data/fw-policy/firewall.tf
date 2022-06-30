resource "google_compute_firewall" "fw-test-800" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  name       = "fw-test-800"
  network    = "default"
  priority   = 800

  source_ranges = ["10.100.0.0/24"]

  deny {
    protocol = "tcp"
    ports    = ["1001-1002"]
  }
}

resource "google_compute_firewall" "fw-test-900" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  name       = "fw-test-900"
  network    = "default"
  priority   = 900

  source_ranges = ["10.100.0.0/24"]
  source_tags   = ["foobar", "foo", "bar"]

  allow {
    protocol = "tcp"
    ports    = ["1234", "1000-2000", "2033"]
  }
}

resource "google_compute_firewall" "fw-test-901" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  name       = "fw-test-901"
  network    = "default"
  priority   = 901

  source_service_accounts = ["service-12340002@compute-system.iam.gserviceaccount.com"]

  allow {
    protocol = "tcp"
    ports    = ["4000"]
  }
}

resource "google_compute_firewall" "fw-test-902" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  name       = "fw-test-902"
  network    = "default"
  priority   = 902

  source_ranges           = ["0.0.0.0/0"]
  target_service_accounts = ["service-12340002@compute-system.iam.gserviceaccount.com"]

  allow {
    protocol = "tcp"
    ports    = ["4001"]
  }
}

resource "google_compute_firewall" "fw-test-903" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  name       = "fw-test-903"
  network    = "default"
  priority   = 903

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["bar"]

  allow {
    protocol = "tcp"
    ports    = ["1234"]
  }
}

resource "google_compute_firewall" "fw-test-950" {
  project    = google_project.project.project_id
  depends_on = [google_project_service.compute]
  name       = "fw-test-950"
  network    = "default"
  priority   = 950

  source_ranges = ["0.0.0.0/0"]

  deny {
    protocol = "tcp"
    ports    = ["1006"]
  }
}
