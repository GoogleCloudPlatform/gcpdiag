# Test data

Many of the tests in gcpdiag are implemented using real API responses that
are fetched with curl and stored in this directory. The API is then mocked
and returns data from the response files (in JSON format).

In order to create the response data, we use real GCP projects. We setup
everything using Terraform, and fetch the responses with curl.

### Creating a new project

To create a new project, proceed as follows (note: this needs to be done
by Googlers in the gcpdiag-dev-team group, reach out to dwes@google.com
if you need something here).

1. Create the project in Cloud Console in the gcpdiag.dev organization.

   - Name: something like: `gcpd-XXXXX-YYYY`, where XXXXX is the name
     of the directory that you are creating, and YYYY is a random suffix
     to make recreation of the project easier (can't reuse names). Example:
     `gcpd-gcf1-s6ew`. For the random suffix, you can use `pwgen -A 4`.
   - Organization: gcpdiag.dev
   - Folder: `gcpdiag-testing`.
   - Billing account: same as for other Cloud Support test projects

1. Create a Cloud Storage Bucket called `PROJECTID-tfstate`, e.g.:
   `gcpd-gcf1-s6ew-tfstate`. This will be used to store Terraform state.

   - Location type: Multi-region
   - Location: us
   - Storage class: standard
   - Access control: uniform
   - Protection tools: none

1. Create a `project.tf` file with the required parameters:

   ```
   terraform {
     backend "gcs" {
       bucket = "gcpd-gcf1-s6ew-tfstate"
     }
   }

   provider "google" {
     project = "gcpd-gcf1-s6ew"
   }

   provider "google-beta" {
     project = "gcpd-gcf1-s6ew"
   }
   ```

1. Run `terraform init` to initialize terraform and then `terraform apply`, etc.
   to create resources. Note: you might need to run `gcloud auth login
   --update-adc` first.
