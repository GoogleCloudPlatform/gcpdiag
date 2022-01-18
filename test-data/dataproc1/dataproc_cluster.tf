resource "google_dataproc_cluster" "good" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "good"
  region     = "us-central1"

  cluster_config {
    master_config {
      num_instances = 1
      machine_type  = "e2-medium"
      disk_config {
        boot_disk_size_gb = 30
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "e2-medium"
      disk_config {
        boot_disk_size_gb = 30
      }
    }
  }
}

resource "google_dataproc_cluster" "test-best-practices-enabled" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "test-best-practices-enabled"
  region     = "us-central1"

  cluster_config {
    master_config {
      num_instances = 1
      machine_type  = "e2-medium"
      disk_config {
        boot_disk_size_gb = 30
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "e2-medium"
      disk_config {
        boot_disk_size_gb = 30
      }
    }
  }
}
resource "google_dataproc_cluster" "test-best-practices-disabled" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "test-best-practices-disabled"
  region     = "us-central1"

  cluster_config {
    master_config {
      num_instances = 1
      machine_type  = "e2-medium"
      disk_config {
        boot_disk_size_gb = 30
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "e2-medium"
      disk_config {
        boot_disk_size_gb = 30
      }
    }

    # Override or set some custom properties
    software_config {
      override_properties = {
        "dataproc:dataproc.logging.stackdriver.enable" = "false"
      }
    }
  }
}
