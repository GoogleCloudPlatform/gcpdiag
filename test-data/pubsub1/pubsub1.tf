resource "google_pubsub_topic" "pubsub1topic" {
  project = google_project.project.project_id
  name    = "gcpdiag-pubsub1topic-${random_string.project_id_suffix.id}"
}

resource "google_pubsub_subscription" "pubsub1subscription" {
  project = google_project.project.project_id
  name    = "gcpdiag-pubsub1subscription-${random_string.project_id_suffix.id}"
  topic   = google_pubsub_topic.pubsub1topic.name
}

data "google_iam_policy" "admin" {
  binding {
    role = "roles/viewer"
    members = [
      "domain:google.com",
    ]
  }
}

resource "google_pubsub_topic_iam_policy" "policy" {
  project     = google_project.project.project_id
  topic       = google_pubsub_topic.pubsub1topic.name
  policy_data = data.google_iam_policy.admin.policy_data
}

resource "google_pubsub_subscription_iam_policy" "policy1" {
  project      = google_project.project.project_id
  subscription = "gcpdiag-pubsub1subscription-${random_string.project_id_suffix.id}"
  policy_data  = data.google_iam_policy.admin.policy_data
}

# BQ subscription

resource "google_project_iam_member" "editor" {
  project  = google_project.project.project_id
  provider = google-beta
  role     = "roles/bigquery.dataEditor"
  member   = "serviceAccount:service-${google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_bigquery_dataset" "pubsub1_dataset" {
  project                     = google_project.project.project_id
  dataset_id                  = "pubsub1_dataset"
  provider                    = google-beta
  default_table_expiration_ms = 2592000000
}

resource "google_bigquery_table" "pubsub1_table" {
  deletion_protection = false
  table_id            = "pubsub1_table"
  project             = google_project.project.project_id
  dataset_id          = google_bigquery_dataset.pubsub1_dataset.dataset_id
  provider            = google-beta

  schema = <<EOF
[
  {
    "name": "data",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "The data"
  }
]
EOF
}

resource "google_pubsub_subscription" "pubsub1subscription2" {
  project  = google_project.project.project_id
  name     = "gcpdiag-pubsub1subscription2-${random_string.project_id_suffix.id}"
  topic    = google_pubsub_topic.pubsub1topic.name
  provider = google-beta

  bigquery_config {
    table = "${google_project.project.project_id}.${google_bigquery_dataset.pubsub1_dataset.dataset_id}.${google_bigquery_table.pubsub1_table.table_id}"
  }

  depends_on = [google_project_iam_member.editor]
}
