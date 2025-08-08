variable "project_id" {
  //default = "use-an-existing-test-project"
}
variable "billing_account_id" {}

variable "org_id" {}
variable "folder_id" { default = "" }

variable "region" {
  type        = string
  description = "The GCP region to create resources in."
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "The GCP zone to create resources in."
  default     = "us-central1-c"
}
