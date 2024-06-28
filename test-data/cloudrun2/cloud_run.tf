# We are not using cloud run terraform resource in this file since we want to make the service to fail to deploy which would break
resource "null_resource" "failed_deployment1" {
  provisioner "local-exec" {
    command = <<-EOT
      cd build_configs/deploy_run_with_bad_container
      gcloud builds submit --project ${google_project.project.project_id} --config cloudbuild.yaml \
        --substitutions _IMAGE=${local.repository_url}/not_http_image
    EOT
  }
  depends_on = [google_artifact_registry_repository.cloudrun_repo]
}

resource "null_resource" "failed_deployment2" {
  provisioner "local-exec" {
    command = <<-EOT
              gcloud run deploy no-image-permission \
                --project ${google_project.project.project_id} \
                --region us-central1 \
                --image gcr.io/private-project/image \
                --no-allow-unauthenticated \
                || true
    EOT
  }
  depends_on = [google_artifact_registry_repository.cloudrun_repo]
}

resource "null_resource" "failed_deployment3" {
  provisioner "local-exec" {
    command = <<-EOT
              gcloud run deploy image-does-not-exist \
                --project ${google_project.project.project_id} \
                --region us-central1 \
                --image ${local.repository_url}/missing-image \
                --no-allow-unauthenticated \
                || true
    EOT
  }
  depends_on = [google_artifact_registry_repository.cloudrun_repo]
}
