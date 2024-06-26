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
