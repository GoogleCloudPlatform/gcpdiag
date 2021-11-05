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
