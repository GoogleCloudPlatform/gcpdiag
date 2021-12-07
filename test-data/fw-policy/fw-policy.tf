resource "google_compute_firewall_policy" "parent" {
  provider   = google-beta
  short_name = "parent-folder-policy"
  parent     = "folders/422810093603"
}

resource "google_compute_firewall_policy" "sub" {
  provider   = google-beta
  short_name = "sub-folder-policy"
  parent     = "folders/392556968391"
}

resource "google_compute_firewall_policy_association" "parent" {
  name              = "parent-association"
  firewall_policy   = google_compute_firewall_policy.parent.id
  attachment_target = google_compute_firewall_policy.parent.parent
}

resource "google_compute_firewall_policy_association" "sub" {
  name              = "sub-association"
  firewall_policy   = google_compute_firewall_policy.sub.id
  attachment_target = google_compute_firewall_policy.sub.parent
}

resource "google_compute_firewall_policy_rule" "parent-1" {
  firewall_policy = google_compute_firewall_policy.parent.id
  description     = "parent-1-rule"
  priority        = 9000
  action          = "allow"
  direction       = "INGRESS"
  match {
    src_ip_ranges = ["10.101.0.1/32"]
    layer4_configs {
      ip_protocol = "tcp"
      ports       = ["2000-2002"]
    }
  }
}

resource "google_compute_firewall_policy_rule" "sub-1" {
  firewall_policy  = google_compute_firewall_policy.sub.id
  description      = "sub-1-rule"
  priority         = 9000
  action           = "allow"
  direction        = "INGRESS"
  target_resources = [data.google_compute_network.default.self_link]
  match {
    src_ip_ranges = ["10.101.0.1/32"]
    layer4_configs {
      ip_protocol = "tcp"
      ports       = ["2003"]
    }
  }
}

resource "google_compute_firewall_policy_rule" "sub-2" {
  firewall_policy         = google_compute_firewall_policy.sub.id
  description             = "sub-1-rule"
  priority                = 8999
  action                  = "allow"
  direction               = "INGRESS"
  target_service_accounts = ["service-12340002@compute-system.iam.gserviceaccount.com"]
  match {
    src_ip_ranges = ["10.102.0.1/32"]
    layer4_configs {
      ip_protocol = "all"
    }
  }
}

resource "google_compute_firewall_policy_rule" "disabled" {
  firewall_policy         = google_compute_firewall_policy.sub.id
  description             = "sub-1-rule"
  priority                = 7000
  action                  = "allow"
  direction               = "INGRESS"
  disabled                = true
  target_service_accounts = ["service-12340002@compute-system.iam.gserviceaccount.com"]
  match {
    src_ip_ranges = ["0.0.0.0/32"]
    layer4_configs {
      ip_protocol = "all"
    }
  }
}
