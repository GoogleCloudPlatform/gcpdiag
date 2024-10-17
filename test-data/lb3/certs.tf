
resource "google_compute_managed_ssl_certificate" "cert1" {
  project = google_project.project.project_id
  name    = "cert1"
  managed {
    domains = ["natka123.com", "second.natka123.com"]
  }
}

resource "google_compute_managed_ssl_certificate" "cert2" {
  project = google_project.project.project_id
  name    = "cert2"
  managed {
    domains = ["test.natka123.com"]
  }
}

resource "google_compute_managed_ssl_certificate" "cert3" {
  project = google_project.project.project_id
  name    = "cert3"
  managed {
    domains = ["test.org", "second.test.org"]
  }
}

resource "google_compute_managed_ssl_certificate" "unused-cert4" {
  project = google_project.project.project_id
  name    = "unused-cert4"
  managed {
    domains = ["test.org", "second.test.org"]
  }
}

resource "google_compute_managed_ssl_certificate" "cert5" {
  project = google_project.project.project_id
  name    = "cert5"
  managed {
    domains = ["test.org"]
  }
}
