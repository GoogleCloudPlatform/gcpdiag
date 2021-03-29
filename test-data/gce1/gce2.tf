resource "google_compute_instance" "default" {
  project        = google_project.project.project_id
  name           = "gce2"
  machine_type   = "f1-micro"
  zone           = "europe-west4-a"
  desired_status = "RUNNING"
  network_interface {
    network = "default"
  }
  scheduling {
    preemptible       = true
    automatic_restart = false
  }
  boot_disk {
    initialize_params {
      image = data.google_compute_image.cos.self_link
    }
  }
  service_account {
    email = data.google_compute_default_service_account.default.email
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol"
    ]
  }
}
