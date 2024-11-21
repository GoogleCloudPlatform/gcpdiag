resource "google_dataproc_cluster" "good" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "good"
  region     = "us-central1"

  cluster_config {
    gce_cluster_config {
      internal_ip_only = false
    }

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
    gce_cluster_config {
      service_account  = google_service_account.sa_worker.email
      zone             = "us-central1-b"
      internal_ip_only = false
    }

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
        # enable cloud monitoring
        "dataproc:dataproc.monitoring.stackdriver.enable" = "true"
      }
    }
  }
}

resource "google_service_account" "sa_worker" {
  project      = google_project.project.project_id
  account_id   = "saworker"
  display_name = "Dataproc VM Service account with Dataproc Worker role"
}

resource "google_project_iam_member" "sa_worker" {
  project = google_project.project.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.sa_worker.email}"
}

resource "google_dataproc_cluster" "test-best-practices-disabled" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "test-best-practices-disabled"
  region     = "us-central1"

  cluster_config {
    gce_cluster_config {
      internal_ip_only = false
    }

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

# Expected to fail on apply, run terraform untaint google_dataproc_cluster.test-deny-icmp then terraform apply again
resource "google_dataproc_cluster" "test-deny-icmp" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "test-deny-icmp"
  region     = "us-central1"

  cluster_config {
    gce_cluster_config {
      zone             = "us-central1-a"
      subnetwork       = google_compute_subnetwork.test-bad-subnet.name
      tags             = ["icmp-deny"]
      internal_ip_only = false
    }
  }
}

resource "google_dataproc_cluster" "job-failed" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "job-failed"
  region     = "us-central1"

  cluster_config {
    gce_cluster_config {
      internal_ip_only = false
    }

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

resource "google_dataproc_cluster" "job-success" {
  depends_on = [google_project_service.dataproc]
  project    = google_project.project.project_id
  name       = "job-success"
  region     = "us-central1"

  cluster_config {
    gce_cluster_config {
      internal_ip_only = false
    }

    master_config {
      num_instances = 1
      machine_type  = "n2-standard-4"
      disk_config {
        boot_disk_size_gb = 30
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "n2-standard-4"
      disk_config {
        boot_disk_size_gb = 30
      }
    }
  }
}
