resource "google_compute_network" "apigee_network" {
  project    = google_project.project.project_id
  name       = "apigee-network"
  depends_on = [google_project_service.compute]
}

resource "google_compute_global_address" "apigee_range" {
  project       = google_project.project.project_id
  name          = "apigee-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 22
  network       = google_compute_network.apigee_network.id
}

resource "google_service_networking_connection" "apigee_vpc_connection" {
  network                 = google_compute_network.apigee_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.apigee_range.name]
  depends_on              = [google_project_service.servicenetworking]
}

resource "google_kms_key_ring" "apigee_keyring" {
  provider   = google
  project    = google_project.project.project_id
  name       = "apigee-keyring"
  location   = "us-central1"
  depends_on = [google_project_service.kms]
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "apigee_key" {
  provider = google
  name     = "apigee-key"
  key_ring = google_kms_key_ring.apigee_keyring.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service_identity" "apigee_sa" {
  provider = google-beta
  project  = google_project.project.project_id
  service  = google_project_service.apigee.service
}

resource "google_kms_crypto_key_iam_binding" "apigee_sa_keyuser" {
  provider      = google
  crypto_key_id = google_kms_crypto_key.apigee_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  members = [
    "serviceAccount:${google_project_service_identity.apigee_sa.email}",
  ]
}

resource "google_apigee_organization" "apigee_org" {
  project_id                           = google_project.project.project_id
  analytics_region                     = "us-central1"
  description                          = "Test Apigee Org for gcpdiag"
  authorized_network                   = google_compute_network.apigee_network.id
  runtime_database_encryption_key_name = google_kms_crypto_key.apigee_key.id
  depends_on = [
    google_service_networking_connection.apigee_vpc_connection,
    google_project_service.apigee
  ]
}

resource "google_apigee_instance" "apigee_instance" {
  name                     = "gcpdiag-apigee1-inst1-${random_string.project_id_suffix.id}"
  location                 = "us-central1"
  description              = "Test Apigee Runtime Instance for gcpdiag"
  org_id                   = google_apigee_organization.apigee_org.id
  disk_encryption_key_name = google_kms_crypto_key.apigee_key.id
}

resource "google_apigee_environment" "apigee_env" {
  org_id = google_apigee_organization.apigee_org.id
  name   = "gcpdiag-demo-env"

  depends_on = [google_project_service.apigee]
}

resource "google_apigee_environment" "apigee_env_1" {
  org_id = google_apigee_organization.apigee_org.id
  name   = "gcpdiag-demo-env-1"

  depends_on = [google_project_service.apigee]
}

resource "google_apigee_instance_attachment" "env_to_instance_attachment" {
  instance_id = google_apigee_instance.apigee_instance.id
  environment = google_apigee_environment.apigee_env.name
}

resource "google_apigee_envgroup" "apigee_envgroup" {
  org_id    = google_apigee_organization.apigee_org.id
  name      = "gcpdiag-demo-envgroup"
  hostnames = ["gcpdiag.apigee.example.com"]

  depends_on = [google_project_service.apigee]
}

resource "google_apigee_envgroup" "apigee_envgroup_1" {
  org_id    = google_apigee_organization.apigee_org.id
  name      = "gcpdiag-demo-envgroup-1"
  hostnames = ["1.gcpdiag.apigee.example.com"]

  depends_on = [google_project_service.apigee]
}

resource "google_apigee_envgroup_attachment" "env_to_envgroup_attachment" {
  envgroup_id = google_apigee_envgroup.apigee_envgroup_1.id
  environment = google_apigee_environment.apigee_env_1.name

  depends_on = [google_project_service.apigee]
}

output "apigee_org_id" {
  value = google_apigee_organization.apigee_org.id
}

output "apigee_instance_id" {
  value = google_apigee_instance.apigee_instance.id
}
