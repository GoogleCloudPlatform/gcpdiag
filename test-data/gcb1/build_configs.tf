resource "local_file" "build1_config" {
  content = templatefile(
    "${path.module}/build_configs/cloudbuild1.yaml.tpl",
    {
      image = "${local.repository_url}/image",
      sa    = google_service_account.service_account_custom1.name
  })
  filename = "${path.module}/build_configs/cloudbuild1.yaml"
}

resource "local_file" "build1b_config" {
  content = templatefile(
    "${path.module}/build_configs/cloudbuild1.yaml.tpl",
    {
      image = "${local.legacy_repository_url}/image",
      sa    = google_service_account.service_account_custom1.name
  })
  filename = "${path.module}/build_configs/cloudbuild1b.yaml"
}

resource "local_file" "build2_config" {
  content = templatefile(
    "${path.module}/build_configs/cloudbuild2.yaml.tpl",
    {
      bucket = google_storage_bucket.bucket_with_retention.name,
  })
  filename = "${path.module}/build_configs/cloudbuild2.yaml"
}

resource "local_file" "build3_config" {
  content = templatefile(
  "${path.module}/build_configs/cloudbuild3.yaml.tpl", {})
  filename = "${path.module}/build_configs/cloudbuild3.yaml"
}

resource "local_file" "build4_config" {
  content = templatefile(
    "${path.module}/build_configs/cloudbuild4.yaml.tpl",
    {
      bucket = google_storage_bucket.bucket_with_retention.name,
  })
  filename = "${path.module}/build_configs/cloudbuild4.yaml"
}

output "build1_config" {
  value = local_file.build1_config.filename
}

output "build1b_config" {
  value = local_file.build1b_config.filename
}

output "build2_config" {
  value = local_file.build2_config.filename
}

output "build3_config" {
  value = local_file.build3_config.filename
}

output "build4_config" {
  value = local_file.build4_config.filename
}
