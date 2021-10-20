data "archive_file" "gcf1source" {
  type        = "zip"
  source_dir  = "sample-code"
  output_path = "gcf1source.zip"
}

resource "google_storage_bucket" "gcf1bucket" {
  project       = "gcpd-gcf1-s6ew"
  name          = "gcpd-gcf1-s6ew-gcf1bucket"
  location      = "US"
  storage_class = "STANDARD"
}

resource "google_storage_bucket_object" "gcf1archive" {
  name   = "gcpd-gcf1-s6ew-gcf1archive"
  bucket = google_storage_bucket.gcf1bucket.name
  source = data.archive_file.gcf1source.output_path
}

resource "google_cloudfunctions_function" "gcf1" {
  project               = "gcpd-gcf1-s6ew"
  name                  = "gcf1"
  region                = "us-central1"
  runtime               = "python39"
  source_archive_bucket = google_storage_bucket.gcf1bucket.name
  source_archive_object = google_storage_bucket_object.gcf1archive.name
  entry_point           = "hello_world"
  trigger_http          = true
  max_instances         = 100
}
