/**
 * Copyright 2021 Google LLC
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

# use this project to maintain terraform state

resource "google_project" "project" {
  name = "gcp-doctor test - terraform"
  # note: we add a "random" 2-byte suffix to make it easy to recreate the
  # project under another name and avoid project name conflicts.
  project_id      = "gcpd-terraform"
  org_id          = "98915863894"
  billing_account = "0072A3-8FBEBA-7CD837"
  skip_delete     = true
}

resource "google_storage_bucket" "gcpd-tf-state" {
  project                     = google_project.project.project_id
  name                        = "gcpd-tf-state"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = true
}
