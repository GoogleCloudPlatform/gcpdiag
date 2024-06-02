/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

variable "org_id" {}

variable "project_id" {
  //default = "use-an-existing-test-project"
}

variable "billing_account_id" {}

variable "region" {
  default = "us-central1"
}

variable "zone" {
  default = "us-central1-a"
}

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
