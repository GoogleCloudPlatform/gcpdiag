resource "google_compute_network" "apigee_network" {
  project                 = google_project.project.project_id
  name                    = "apigee-network"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.compute]
}

resource "google_compute_subnetwork" "apigee_subnetwork" {
  project                  = google_project.project.project_id
  name                     = "apigee-subnetwork"
  region                   = "us-central1"
  ip_cidr_range            = "10.128.0.0/20"
  network                  = google_compute_network.apigee_network.id
  private_ip_google_access = true
  depends_on = [google_project_service.compute,
  google_compute_network.apigee_network]
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

resource "google_compute_instance_template" "mig_bridge_template" {
  project      = google_project.project.project_id
  name_prefix  = "mig-bridge-us-central1-"
  machine_type = "e2-small"
  tags         = ["https-server", "mig-bridge"]
  disk {
    source_image = "centos-cloud/centos-7"
    boot         = true
    disk_size_gb = 20
  }
  network_interface {
    network    = google_compute_network.apigee_network.id
    subnetwork = google_compute_subnetwork.apigee_subnetwork.id
  }
  metadata = {
    ENDPOINT           = google_apigee_instance.apigee_instance.host
    startup-script-url = "gs://apigee-5g-saas/apigee-envoy-proxy-release/latest/conf/startup-script.sh"
  }
  service_account {
    scopes = ["storage-ro"]
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_region_instance_group_manager" "mig_bridge_manager" {
  name               = "mig-bridge-manager-us-central1"
  project            = google_project.project.project_id
  base_instance_name = "mig-bridge-us-central1"
  region             = "us-central1"
  version {
    instance_template = google_compute_instance_template.mig_bridge_template.id
  }
  named_port {
    name = "apigee-https"
    port = 443
  }
}

resource "google_compute_region_autoscaler" "mig_bridge_autoscaler" {
  name    = "mig-autoscaler-us-central1"
  project = google_project.project.project_id
  region  = "us-central1"
  target  = google_compute_region_instance_group_manager.mig_bridge_manager.id
  autoscaling_policy {
    max_replicas    = 10
    min_replicas    = 2
    cooldown_period = 90
    cpu_utilization {
      target = 0.75
    }
  }
}


output "apigee_org_id" {
  value = google_apigee_organization.apigee_org.id
}

output "apigee_instance_id" {
  value = google_apigee_instance.apigee_instance.id
}
