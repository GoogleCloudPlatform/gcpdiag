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
