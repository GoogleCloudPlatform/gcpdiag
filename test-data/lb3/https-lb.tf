# External HTTP load balancer

# [START cloudloadbalancing_ext_http_gce_instance_template]
resource "google_compute_instance_template" "default" {
  depends_on = [google_project_service.compute]
  name       = "lb-backend-template"
  project    = google_project.project.project_id
  disk {
    auto_delete  = true
    boot         = true
    device_name  = "persistent-disk-0"
    mode         = "READ_WRITE"
    source_image = "projects/debian-cloud/global/images/family/debian-11"
    type         = "PERSISTENT"
  }
  labels = {
    managed-by-cnrm = "true"
  }
  machine_type = "n1-standard-1"
  metadata = {
    startup-script = "#! /bin/bash\n     sudo apt-get update\n     sudo apt-get install apache2 -y\n     sudo a2ensite default-ssl\n     sudo a2enmod ssl\n     sudo vm_hostname=\"$(curl -H \"Metadata-Flavor:Google\" \\\n   http://169.254.169.254/computeMetadata/v1/instance/name)\"\n   sudo echo \"Page served from: $vm_hostname\" | \\\n   tee /var/www/html/index.html\n   sudo systemctl restart apache2"
  }
  network_interface {
    access_config {
      network_tier = "PREMIUM"
    }
    network = "default"
    #subnetwork = "regions/us-east1/subnetworks/default"
  }
  region = "us-east1"
  service_account {
    email  = "default"
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/pubsub", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/trace.append"]
  }
  tags = ["allow-health-check"]
}
# [END cloudloadbalancing_ext_http_gce_instance_template]

# [START cloudloadbalancing_ext_http_gce_instance_mig]
resource "google_compute_instance_group_manager" "default" {
  depends_on = [google_project_service.compute]
  project    = google_project.project.project_id
  name       = "lb-backend-example"
  zone       = "us-east1-b"
  named_port {
    name = "http"
    port = 80
  }
  version {
    instance_template = google_compute_instance_template.default.id
    name              = "primary"
  }
  base_instance_name = "vm"
  target_size        = 2
}
# [END cloudloadbalancing_ext_http_gce_instance_mig]

# [START cloudloadbalancing_ext_http_gce_instance_ip_address]
resource "google_compute_global_address" "default" {
  depends_on = [google_project_service.compute]
  project    = google_project.project.project_id
  name       = "lb-ipv4-1"
  ip_version = "IPV4"
}
# [END cloudloadbalancing_ext_http_gce_instance_ip_address]

# [START cloudloadbalancing_ext_http_gce_instance_ip_address]
resource "google_compute_global_address" "ipv6-address" {
  depends_on = [google_project_service.compute]
  project    = google_project.project.project_id
  name       = "lb-ipv6-1"
  ip_version = "IPV6"
}
# [END cloudloadbalancing_ext_http_gce_instance_ip_address]

# [START cloudloadbalancing_ext_http_gce_instance_health_check]
resource "google_compute_health_check" "default" {
  depends_on         = [google_project_service.compute]
  name               = "http-basic-check"
  project            = google_project.project.project_id
  check_interval_sec = 5
  healthy_threshold  = 2

  http_health_check {
    # port different than the one in the backend service
    port               = 88
    port_specification = "USE_FIXED_PORT"
    proxy_header       = "NONE"
    request_path       = "/"
  }

  log_config {
    enable = true
  }

  timeout_sec         = 5
  unhealthy_threshold = 2
}
# [END cloudloadbalancing_ext_http_gce_instance_health_check]

# [START cloudloadbalancing_ext_http_gce_instance_backend_service]
resource "google_compute_backend_service" "default" {
  name                            = "web-backend-service"
  project                         = google_project.project.project_id
  connection_draining_timeout_sec = 0
  health_checks                   = [google_compute_health_check.default.id]
  load_balancing_scheme           = "EXTERNAL"
  port_name                       = "http"
  protocol                        = "HTTP"
  session_affinity                = "NONE"
  timeout_sec                     = 30
  backend {
    group           = google_compute_instance_group_manager.default.instance_group
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
  }
}
# [END cloudloadbalancing_ext_http_gce_instance_backend_service]

resource "google_certificate_manager_certificate_map" "default" {
  project     = google_project.project.project_id
  name        = "cert-map"
  description = "My acceptance test certificate map"
  labels = {
    "terraform" : true,
    "acc-test" : true,
  }
}

# [START cloudloadbalancing_ext_http_gce_instance_url_map]
resource "google_compute_url_map" "default" {
  project         = google_project.project.project_id
  name            = "web-map-https"
  default_service = google_compute_backend_service.default.id
}
# [END cloudloadbalancing_ext_http_gce_instance_url_map]

# [START cloudloadbalancing_ext_http_gce_instance_target_https_proxy]
resource "google_compute_target_https_proxy" "default" {
  project          = google_project.project.project_id
  name             = "https-lb-proxy"
  url_map          = google_compute_url_map.default.id
  certificate_map  = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.default.id}"
  ssl_certificates = [google_compute_managed_ssl_certificate.cert1.id]
}
# [END cloudloadbalancing_ext_http_gce_instance_target_https_proxy]

# [START cloudloadbalancing_ext_http_gce_instance_forwarding_rule]
resource "google_compute_global_forwarding_rule" "default" {
  project               = google_project.project.project_id
  name                  = "https-content-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "443-443"
  target                = google_compute_target_https_proxy.default.id
  ip_address            = google_compute_global_address.default.id
}
# [END cloudloadbalancing_ext_http_gce_instance_forwarding_rule]


# [START cloudloadbalancing_ext_http_gce_instance_target_https_proxy]
resource "google_compute_target_https_proxy" "working-cert" {
  project          = google_project.project.project_id
  name             = "https-lb-proxy-working"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.cert2.id]
}
# [END cloudloadbalancing_ext_http_gce_instance_target_https_proxy]

# [START cloudloadbalancing_ext_http_gce_instance_forwarding_rule]
resource "google_compute_global_forwarding_rule" "working-cert" {
  project               = google_project.project.project_id
  name                  = "https-content-rule-working"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "80-80"
  target                = google_compute_target_https_proxy.working-cert.id
  ip_address            = google_compute_global_address.ipv6-address.id
}
# [END cloudloadbalancing_ext_http_gce_instance_forwarding_rule]
