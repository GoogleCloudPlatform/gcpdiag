resource "google_dataflow_job" "wordcount" {
  project           = google_project.project.project_id
  region            = "us-central1"
  zone              = "us-central1-a"
  name              = "wordcount"
  template_gcs_path = "gs://dataflow-templates/latest/Word_Count"
  temp_gcs_location = "gs://${google_storage_bucket.dataflow_out.name}/temp"
  parameters = {
    inputFile = "gs://dataflow-samples/shakespeare/kinglear.txt"
    output    = "gs://${google_storage_bucket.dataflow_out.name}/wordcount/output"
  }
}
