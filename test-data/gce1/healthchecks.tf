# [START cloudloadbalancing_ext_http_gce_instance_health_check]
resource "google_compute_health_check" "default" {
  provider           = google-beta
  depends_on         = [google_project_service.compute]
  name               = "http-basic-check"
  project            = google_project.project.project_id
  check_interval_sec = 5
  healthy_threshold  = 2

  http_health_check {
    port               = 80
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

# [START cloudloadbalancing_ext_http_gce_instance_health_check]
resource "google_compute_health_check" "http-basic-check-2" {
  depends_on         = [google_project_service.compute]
  name               = "http-basic-check-2"
  project            = google_project.project.project_id
  check_interval_sec = 5
  healthy_threshold  = 2

  http_health_check {
    port               = 80
    port_specification = "USE_FIXED_PORT"
    proxy_header       = "NONE"
    request_path       = "/"
  }

  timeout_sec         = 5
  unhealthy_threshold = 2
}
# [END cloudloadbalancing_ext_http_gce_instance_health_check]

# [START cloudloadbalancing_ext_tcp_gce_instance_health_check]
resource "google_compute_health_check" "tcp-basic-check-1" {
  provider   = google-beta
  depends_on = [google_project_service.compute]
  name       = "tcp-basic-check-1"
  project    = google_project.project.project_id

  check_interval_sec = 5
  timeout_sec        = 5

  tcp_health_check {
    port = 80
  }

  log_config {
    enable = true
  }

}
# [END cloudloadbalancing_ext_tcp_gce_instance_health_check]
