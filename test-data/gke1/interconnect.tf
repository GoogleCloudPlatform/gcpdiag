# Terraform configuration for Interconnect resources used in tests.

resource "google_compute_router" "dummy_router1" {
  name    = "dummy-router1"
  project = google_project.project.project_id
  region  = "us-east4"
  network = data.google_compute_network.default.id
}

resource "google_compute_router" "dummy_router2" {
  name    = "dummy-router2"
  project = google_project.project.project_id
  region  = "us-east4"
  network = data.google_compute_network.default.id
}

resource "google_compute_router" "dummy_router3" {
  name    = "dummy-router3"
  project = google_project.project.project_id
  region  = "us-west2"
  network = data.google_compute_network.default.id
}

resource "google_compute_interconnect" "dummy_interconnect1" {
  name                 = "dummy-interconnect1"
  project              = google_project.project.project_id
  customer_name        = "Dummy User"
  interconnect_type    = "IT_PRIVATE"
  link_type            = "LINK_TYPE_ETHERNET_10G_LR"
  location             = "bos-zone1-219"
  requested_link_count = 1
}

resource "google_compute_interconnect" "dummy_interconnect2" {
  name                 = "dummy-interconnect2"
  project              = google_project.project.project_id
  customer_name        = "Dummy User"
  interconnect_type    = "IT_PRIVATE"
  link_type            = "LINK_TYPE_ETHERNET_10G_LR"
  location             = "bos-zone2-219"
  requested_link_count = 1
}

resource "google_compute_interconnect" "dummy_interconnect3" {
  name                 = "dummy-interconnect3"
  project              = google_project.project.project_id
  customer_name        = "Dummy User"
  interconnect_type    = "IT_PRIVATE"
  link_type            = "LINK_TYPE_ETHERNET_10G_LR"
  location             = "sjc-zone1-6"
  requested_link_count = 1
}

resource "google_compute_interconnect" "dummy_interconnect4" {
  name                 = "dummy-interconnect4"
  project              = google_project.project.project_id
  customer_name        = "Dummy User"
  interconnect_type    = "IT_PRIVATE"
  link_type            = "LINK_TYPE_ETHERNET_10G_LR"
  location             = "sjc-zone2-6"
  requested_link_count = 1
}

# dummy-interconnect5 in JSON points to dummy-interconnect4 selfLink, but we define it uniquely here.
resource "google_compute_interconnect" "dummy_interconnect5" {
  name                 = "dummy-interconnect5"
  project              = google_project.project.project_id
  customer_name        = "Dummy User"
  interconnect_type    = "IT_PRIVATE"
  link_type            = "LINK_TYPE_ETHERNET_10G_LR"
  location             = "sjc-zone2-6"
  requested_link_count = 1
}

resource "google_compute_interconnect_attachment" "dummy_attachment1" {
  name          = "dummy-attachment1"
  project       = google_project.project.project_id
  region        = "us-east4"
  router        = google_compute_router.dummy_router1.id
  interconnect  = google_compute_interconnect.dummy_interconnect1.id
  type          = "DEDICATED"
  vlan_tag8021q = 1101
  mtu           = 1460
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment2" {
  name          = "dummy-attachment2"
  project       = google_project.project.project_id
  region        = "us-east4"
  router        = google_compute_router.dummy_router1.id
  interconnect  = google_compute_interconnect.dummy_interconnect1.id
  type          = "DEDICATED"
  vlan_tag8021q = 1103
  mtu           = 1460
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment3" {
  name          = "dummy-attachment3"
  project       = google_project.project.project_id
  region        = "us-east4"
  router        = google_compute_router.dummy_router2.id
  interconnect  = google_compute_interconnect.dummy_interconnect2.id
  type          = "DEDICATED"
  vlan_tag8021q = 1105
  mtu           = 1460
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment4" {
  name          = "dummy-attachment4"
  project       = google_project.project.project_id
  region        = "us-east4"
  router        = google_compute_router.dummy_router2.id
  interconnect  = google_compute_interconnect.dummy_interconnect2.id
  type          = "DEDICATED"
  vlan_tag8021q = 1106
  mtu           = 1460
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment5" {
  name          = "dummy-attachment5"
  project       = google_project.project.project_id
  region        = "us-west2"
  router        = google_compute_router.dummy_router3.id
  interconnect  = google_compute_interconnect.dummy_interconnect3.id
  type          = "DEDICATED"
  vlan_tag8021q = 1102
  mtu           = 1450
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment6" {
  name          = "dummy-attachment6"
  project       = google_project.project.project_id
  region        = "us-west2"
  router        = google_compute_router.dummy_router3.id
  interconnect  = google_compute_interconnect.dummy_interconnect4.id
  type          = "DEDICATED"
  vlan_tag8021q = 1104
  mtu           = 1440
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment7" {
  name          = "dummy-attachment7"
  project       = google_project.project.project_id
  region        = "us-west2"
  router        = google_compute_router.dummy_router3.id
  interconnect  = google_compute_interconnect.dummy_interconnect4.id
  type          = "DEDICATED"
  vlan_tag8021q = 1107
  mtu           = 1440
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment8" {
  name          = "dummy-attachment8"
  project       = google_project.project.project_id
  region        = "us-west2"
  router        = google_compute_router.dummy_router3.id
  interconnect  = google_compute_interconnect.dummy_interconnect4.id
  type          = "DEDICATED"
  vlan_tag8021q = 1108
  mtu           = 1440
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment9" {
  name          = "dummy-attachment9"
  project       = google_project.project.project_id
  region        = "us-west2"
  router        = google_compute_router.dummy_router3.id
  interconnect  = google_compute_interconnect.dummy_interconnect4.id
  type          = "DEDICATED"
  vlan_tag8021q = 1109
  mtu           = 1440
  admin_enabled = true
}

resource "google_compute_interconnect_attachment" "dummy_attachment10" {
  name          = "dummy-attachment10"
  project       = google_project.project.project_id
  region        = "us-west2"
  router        = google_compute_router.dummy_router3.id
  interconnect  = google_compute_interconnect.dummy_interconnect4.id
  type          = "DEDICATED"
  vlan_tag8021q = 1110
  mtu           = 1440
  admin_enabled = true
}
