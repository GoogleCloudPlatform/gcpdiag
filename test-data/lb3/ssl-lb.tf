resource "google_compute_global_address" "ssl-address" {
  depends_on = [google_project_service.compute]
  project    = google_project.project.project_id
  name       = "lb-ssl-ip"
  ip_version = "IPV4"
}


resource "google_compute_global_forwarding_rule" "ssl-rule" {
  project               = google_project.project.project_id
  name                  = "ssl-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "443-443"
  target                = google_compute_target_ssl_proxy.ssl-proxy.id
  ip_address            = google_compute_global_address.ssl-address.id
}

resource "google_compute_target_ssl_proxy" "ssl-proxy" {
  project          = google_project.project.project_id
  name             = "ssl-proxy"
  ssl_certificates = [google_compute_managed_ssl_certificate.cert3.id, google_compute_managed_ssl_certificate.cert5.id]
  backend_service  = google_compute_backend_service.tcp-backend-service.id
}

resource "google_compute_backend_service" "tcp-backend-service" {
  name                            = "tcp-backend-service"
  project                         = google_project.project.project_id
  connection_draining_timeout_sec = 0
  health_checks                   = [google_compute_health_check.default.id]
  load_balancing_scheme           = "EXTERNAL_MANAGED"
  port_name                       = "http"
  protocol                        = "TCP"
  session_affinity                = "NONE"
  timeout_sec                     = 30
  backend {
    group           = google_compute_instance_group_manager.default.instance_group
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
  }
}
