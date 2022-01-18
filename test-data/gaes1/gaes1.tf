resource "google_app_engine_standard_app_version" "version1" {
  version_id = "v1"
  service    = "default"
  runtime    = "python39"

  project = "gcpdiag-gaes1-vvdo0yn5"

  entrypoint {
    shell = "python ./main.py"
  }

  deployment {
    zip {
      source_url = "https://storage.googleapis.com/gaes1-bucket/hello_world.zip"
    }
  }

  env_variables = {
    port = "8080"
  }

  automatic_scaling {
    min_idle_instances = 0
    max_idle_instances = 1
  }

  delete_service_on_destroy = true
}
