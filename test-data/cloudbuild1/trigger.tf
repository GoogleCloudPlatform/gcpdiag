resource "google_cloudbuild_trigger" "trigger" {
  trigger_template {
    branch_name = "main"
    repo_name   = "test-repo"
  }
  build {
    step {
      name = "gcr.io/cloud-builders/gsutil"
    }
  }
  project = "gcpdiag-cloudbuild1-3kag9l6k"
}
