variable "project_id" {
  //default = "use-an-existing-test-project"
  //project_id = gcpdiag-gce-vm-performance
}
variable "billing_account_id" {}

variable "org_id" {}
variable "folder_id" { default = "" }

variable "roles" {
  description = "List of SSH related roles to assign"
  type        = list(string)
  default = [
    "roles/owner",
    "roles/compute.osLogin",
    "roles/compute.osAdminLogin",
    "roles/iam.serviceAccountUser",
    "roles/iap.tunnelResourceAccessor",
    "roles/compute.instanceAdmin.v1",
  ]
}
