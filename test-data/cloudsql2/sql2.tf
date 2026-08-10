resource "google_compute_network" "private_network" {
  project                 = google_project.project.project_id
  name                    = "private-network"
  auto_create_subnetworks = "false"
}

resource "google_compute_global_address" "private_ip_address" {
  project       = google_project.project.project_id
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 20
  network       = google_compute_network.private_network.id
  address       = "172.17.0.0"

  depends_on = [
    google_project_service.compute,
    google_compute_network.private_network
  ]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.private_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]

  depends_on = [
    google_project_service.servicenetworking,
    google_compute_global_address.private_ip_address
  ]
}

resource "google_sql_database_instance" "sql1" {
  project          = google_project.project.project_id
  name             = "sql1"
  region           = "us-central1"
  database_version = "MYSQL_8_0"

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql2" {
  project          = google_project.project.project_id
  name             = "sql2"
  region           = "us-central1"
  database_version = "MYSQL_8_0"

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-g1-small"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql3" {
  project          = google_project.project.project_id
  name             = "sql3"
  region           = "us-central1"
  database_version = "MYSQL_8_0"

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
    maintenance_window {
      day  = 7
      hour = 4
    }
  }
}

resource "google_sql_database_instance" "sql4" {
  project          = google_project.project.project_id
  name             = "sql4"
  region           = "us-central1"
  database_version = "MYSQL_5_7"

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier              = "db-n1-standard-1"
    availability_type = "REGIONAL"
    backup_configuration {
      enabled            = true
      binary_log_enabled = true
    }
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql5" {
  project              = google_project.project.project_id
  name                 = "sql5"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = google_sql_database_instance.sql3.name

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql6" {
  project              = google_project.project.project_id
  name                 = "sql6"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = google_sql_database_instance.sql3.name

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql7" {
  project              = google_project.project.project_id
  name                 = "sql7"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = "gcpdiag-cloudsql1-aaaa:sql1"

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql8" {
  project              = google_project.project.project_id
  name                 = "sql8"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = "other-project:sql1"

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql9" {
  project              = google_project.project.project_id
  name                 = "sql9"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = google_sql_database_instance.sql1.name

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql10" {
  project              = google_project.project.project_id
  name                 = "sql10"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = google_sql_database_instance.sql3.name

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

resource "google_sql_database_instance" "sql11" {
  project              = google_project.project.project_id
  name                 = "sql11"
  region               = "us-central1"
  database_version     = "MYSQL_8_0"
  master_instance_name = google_sql_database_instance.sql1.name

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-n1-standard-1"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }
  }
}

provider "google-beta" {
  region = "us-central1"
  zone   = "us-central1-a"
}
