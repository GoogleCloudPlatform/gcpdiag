
resource "google_compute_network_endpoint" "default-endpoint" {
  project                = google_project.project.project_id
  network_endpoint_group = google_compute_network_endpoint_group.neg1.name
  zone                   = "europe-west4-b"

  instance   = google_compute_instance.neg-vm.name
  port       = google_compute_network_endpoint_group.neg1.default_port
  ip_address = google_compute_instance.neg-vm.network_interface[0].network_ip
}

resource "google_compute_instance" "neg-vm" {
  project = google_project.project.project_id

  name           = "neg-vm"
  machine_type   = "e2-medium"
  zone           = "europe-west4-b"
  desired_status = "RUNNING"
  network_interface {
    subnetwork_project = google_project.project.project_id
    subnetwork         = "default"
  }

  boot_disk {
    initialize_params {
      image = data.google_compute_image.windows.self_link
    }
  }
  depends_on = [google_project_service.compute]

}

resource "google_compute_network_endpoint_group" "neg1" {
  project      = google_project.project.project_id
  name         = "neg1"
  network      = "default"
  subnetwork   = "default"
  default_port = "90"
  zone         = "europe-west4-b"
  depends_on   = [google_project_service.compute]
}
