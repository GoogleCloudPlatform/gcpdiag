# Terraform configuration for GKE maintenance policy test clusters

resource "google_container_cluster" "gke_short" {
  provider           = google
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke-short"
  location           = "europe-west4-a"
  initial_node_count = 1

  node_config {
    machine_type = "n1-standard-2"
    guest_accelerator {
      type  = "nvidia-tesla-v100"
      count = 1
    }
  }

  maintenance_policy {
    recurring_window {
      start_time = "2023-02-01T09:00:00Z"
      end_time   = "2023-02-01T10:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    }
  }

  resource_labels = {
    gcpdiag_test = "gke"
  }
}

resource "google_container_cluster" "gke_expired" {
  provider           = google
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke-expired"
  location           = "europe-west4-a"
  initial_node_count = 1

  node_config {
    machine_type = "n1-standard-2"
    guest_accelerator {
      type  = "nvidia-tesla-v100"
      count = 1
    }
  }

  maintenance_policy {
    recurring_window {
      start_time = "2023-02-01T09:00:00Z"
      end_time   = "2023-02-01T17:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;UNTIL=20230101T000000Z"
    }
  }

  resource_labels = {
    gcpdiag_test = "gke"
  }
}
