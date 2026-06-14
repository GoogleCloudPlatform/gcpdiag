resource "google_bigquery_table" "test_table" {
  project    = "gcpdiag-bigquery1-aaaa"
  dataset_id = "test_dataset"
  table_id   = "test_table"
}

resource "google_bigquery_dataset" "test_dataset" {
  project       = "gcpdiag-bigquery1-aaaa"
  dataset_id    = "test_dataset"
  friendly_name = "test"
  description   = "This is a test description"
  location      = "US"
}

resource "google_bigquery_job" "job" {
  project = "gcpdiag-bigquery1-aaaa"
  job_id  = "job_query_1"

  query {
    query = "SELECT * FROM [bigquery-public-data.america_health_rankings.ahr] LIMIT 10"

    destination_table {
      project_id = "gcpdiag-bigquery1-aaaa"
      dataset_id = "test_dataset"
      table_id   = "test_table"
    }

    allow_large_results = true
    flatten_results     = true

    script_options {
      key_result_statement = "LAST"
    }
  }
}
