variable "billing_account_id" {}

variable "org_id" {}
variable "folder_id" { default = "" }
variable "project_id" {}

variable "roles" {
  description = "List of logging and monitoring related roles to assign to default SA"
  type        = list(string)
  default = [
    "roles/owner",
    "roles/logging.admin",
    "roles/logging.logWriter",
    "roles/monitoring.admin",
    "roles/monitoring.metricWriter"
  ]
}
