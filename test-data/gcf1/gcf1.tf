data "archive_file" "gcf1source" {
  type        = "zip"
  source_dir  = "sample-code"
  output_path = "gcf1source.zip"
}

resource "google_storage_bucket" "gcf1bucket" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcf1bucket-${random_string.project_id_suffix.id}"
  location      = "US"
  storage_class = "STANDARD"
}

resource "google_storage_bucket_object" "gcf1archive" {
  name   = "gcpdiag-gcf1archive"
  bucket = google_storage_bucket.gcf1bucket.name
  source = data.archive_file.gcf1source.output_path
}

resource "google_cloudfunctions_function" "gcf1" {
  project               = google_project.project.project_id
  depends_on            = [google_project_service.cloudfunctions]
  name                  = "gcf1"
  region                = "us-central1"
  runtime               = "python39"
  source_archive_bucket = google_storage_bucket.gcf1bucket.name
  source_archive_object = google_storage_bucket_object.gcf1archive.name
  entry_point           = "hello_world"
  trigger_http          = true
  max_instances         = 100
}
