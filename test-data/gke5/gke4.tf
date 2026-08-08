resource "google_container_cluster" "gke4" {
  provider           = google-beta
  project            = google_project.project.project_id
  depends_on         = [google_project_service.container]
  name               = "gke4"
  location           = "europe-west4-a"
  initial_node_count = 1
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = "/14"
    services_ipv4_cidr_block = "/20"
  }
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "10.0.1.0/28"
  }
  workload_identity_config {
    workload_pool = "${google_project.project.project_id}.svc.id.goog"
  }
}

# configure cloud nat

data "google_compute_network" "default" {
  name    = "default"
  project = google_project.project.project_id

  depends_on = [google_project_service.compute]
}

data "google_compute_subnetwork" "default" {
  name    = "default"
  project = google_project.project.project_id
  region  = "europe-west4"

  depends_on = [google_project_service.compute]
}

resource "google_compute_router" "router" {
  name    = "gke-default-router"
  project = google_project.project.project_id
  region  = "europe-west4"
  network = data.google_compute_network.default.id
}

resource "google_compute_router_nat" "nat" {
  name                   = "gke-default-router-nat"
  project                = google_project.project.project_id
  router                 = google_compute_router.router.name
  region                 = google_compute_router.router.region
  nat_ip_allocate_option = "AUTO_ONLY"

  # source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = data.google_compute_subnetwork.default.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}

# configure internal ingress for simple web application

# authenticate kubernetes provider with cluster
data "google_client_config" "gke4" {
  depends_on = [google_container_cluster.gke4]
}

data "google_container_cluster" "gke4" {
  project    = google_project.project.project_id
  name       = "gke4"
  location   = "europe-west4-a"
  depends_on = [google_container_cluster.gke4]
}

provider "kubernetes" {
  alias = "gke4"
  host  = "https://${data.google_container_cluster.gke4.endpoint}"
  token = data.google_client_config.gke4.access_token
  cluster_ca_certificate = base64decode(
    data.google_container_cluster.gke4.master_auth[0].cluster_ca_certificate,
  )
}

# configure simple web application
resource "kubernetes_deployment" "web_at_gke4" {
  provider = kubernetes.gke4
  metadata {
    name      = "web"
    namespace = "default"
  }
  spec {
    replicas = 2
    selector {
      match_labels = {
        run = "web"
      }
    }
    template {
      metadata {
        labels = {
          run = "web"
        }
      }
      spec {
        container {
          image = "us-docker.pkg.dev/google-samples/containers/gke/hello-app:1.0"
          name  = "web"
          port {
            container_port = 8080
          }
        }
      }
    }
  }
  depends_on = [google_container_cluster.gke4]
}

resource "kubernetes_service" "web_at_gke4" {
  provider = kubernetes.gke4
  metadata {
    name      = "web"
    namespace = "default"
    annotations = {
      "cloud.google.com/neg" = jsonencode(
        {
          ingress = true
        }
      )
    }
  }
  spec {
    selector = {
      run = "web"
    }
    type = "NodePort"
    port {
      port        = 8080
      target_port = 8080
    }
  }
  depends_on = [google_container_cluster.gke4]
}

resource "kubernetes_ingress_v1" "web_at_gke4" {
  provider = kubernetes.gke4
  metadata {
    name      = "web"
    namespace = "default"
    annotations = {
      "kubernetes.io/ingress.class" = "gce-internal"
    }
  }
  spec {
    default_backend {
      service {
        name = "web"
        port {
          number = 8080
        }
      }
    }
  }
  depends_on = [google_container_cluster.gke4]
}

resource "google_compute_firewall" "ingress_test_deny" {
  name    = "gke-gke4-ingress-test-deny"
  network = "default"
  project = google_project.project.project_id

  priority = 900

  deny {
    ports    = ["1024-10000"]
    protocol = "tcp"
  }

  source_ranges = ["35.191.0.0/16"]

  depends_on = [google_project_service.compute]
}
