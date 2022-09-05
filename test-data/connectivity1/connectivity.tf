resource "google_network_management_connectivity_test" "conn-test-instances" {
  name    = "gcpdiag-conn-test-delivered"
  project = google_project.project.project_id
  source {
    instance = google_compute_instance.source.id
  }

  destination {
    instance = google_compute_instance.destination.id
  }

  protocol = "TCP"
}

resource "google_compute_instance" "source" {
  name         = "source-vm"
  machine_type = "e2-medium"
  project      = google_project.project.project_id
  zone         = "us-central1-a"
  depends_on   = [google_project_service.compute]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-10"
    }
  }

  network_interface {
    network = "default"
  }
}

resource "google_compute_instance" "destination" {
  name         = "dest-vm"
  machine_type = "e2-medium"
  project      = google_project.project.project_id
  zone         = "us-central1-a"
  depends_on   = [google_project_service.compute]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-10"
    }
  }

  network_interface {
    network = "default"
  }
}
