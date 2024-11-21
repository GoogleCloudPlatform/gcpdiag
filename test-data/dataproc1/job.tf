resource "google_dataproc_job" "job-failed" {
  region       = google_dataproc_cluster.job-failed.region
  project      = google_dataproc_cluster.job-failed.project
  force_delete = true
  placement {
    cluster_name = google_dataproc_cluster.job-failed.name
  }

  spark_config {
    main_class    = "org.apache.spark.examples.SparkPi"
    jar_file_uris = ["file:///usr/lib/spark/examples/jars/spark-examples.jar"]
    args          = ["10000"]

    properties = {
      "spark.logConf" = "true"
    }

    logging_config {
      driver_log_levels = {
        "root" = "INFO"
      }
    }
  }
}

resource "google_dataproc_job" "job-success" {
  region       = google_dataproc_cluster.job-success.region
  project      = google_dataproc_cluster.job-success.project
  force_delete = true
  placement {
    cluster_name = google_dataproc_cluster.job-success.name
  }

  spark_config {
    main_class    = "org.apache.spark.examples.SparkPi"
    jar_file_uris = ["file:///usr/lib/spark/examples/jars/spark-examples.jar"]
    args          = ["10"]

    properties = {
      "spark.logConf" = "true"
    }

    logging_config {
      driver_log_levels = {
        "root" = "INFO"
      }
    }
  }
}

output "job-failed-id" {
  value = google_dataproc_job.job-failed.reference[0].job_id
}

output "job-success-id" {
  value = google_dataproc_job.job-success.reference[0].job_id
}
