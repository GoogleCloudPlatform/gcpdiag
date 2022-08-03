data "archive_file" "gcf2source" {
  type        = "zip"
  source_dir  = "sourcecode"
  output_path = "gcf2source.zip"
}

resource "google_storage_bucket" "gcf2bucket" {
  project       = google_project.project.project_id
  name          = "gcpdiag-gcf2bucket-${random_string.project_id_suffix.id}"
  location      = "EUROPE-WEST2"
  storage_class = "STANDARD"
}

resource "google_storage_bucket_object" "gcf2archive" {
  name   = "gcpdiag-gcf2archive"
  bucket = google_storage_bucket.gcf2bucket.name
  source = "gcf2source.zip"
}

resource "google_cloudfunctions_function" "gcf2" {
  project               = google_project.project.project_id
  depends_on            = [google_project_service.cloudfunctions]
  name                  = "gcf2"
  region                = "europe-west2"
  runtime               = "python39"
  source_archive_bucket = google_storage_bucket.gcf2bucket.name
  source_archive_object = google_storage_bucket_object.gcf2archive.name
  entry_point           = "gcf_mem_alloc"
  trigger_http          = true
  max_instances         = 100
}
