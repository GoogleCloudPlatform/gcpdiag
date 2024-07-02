# https://cloud.google.com/dataflow/docs/guides/templates/provided-templates
# https://cloud.google.com/dataflow/docs/guides/templates/using-flex-templates

resource "google_dataflow_job" "gcs_to_pubsub_dataflow_streaming" {
  project           = google_project.project.project_id
  region            = "us-central1"
  zone              = "us-central1-a"
  name              = "gcs_to_pubsub"
  template_gcs_path = "gs://dataflow-templates-europe-north1/latest/Stream_GCS_Text_to_Cloud_PubSub"
  temp_gcs_location = "gs://${google_storage_bucket.dataflow_streaming.name}/gcs_to_pubsub/temp"
  parameters = {
    inputFilePattern = "${google_storage_bucket.dataflow_streaming.url}/input/*.json"
    outputTopic      = google_pubsub_topic.topic.id
  }
  transform_name_mapping = {
    name = "test_job"
    env  = "test"
  }
  on_delete = "cancel"
}

resource "google_pubsub_topic" "topic" {
  name    = "dataflow-job-streaming"
  project = google_project.project.project_id
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/dataflow_job
