# gcpdiag - Diagnostics for Google Cloud Platform

[![code analysis badge](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/code-analysis.yml/badge.svg?branch=main&event=push)](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/code-analysis.yml?query=branch%3Amain+event%3Apush)
[![test badge](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/GoogleCloudPlatform/gcpdiag/badge)](https://scorecard.dev/viewer/?uri=github.com/GoogleCloudPlatform/gcpdiag)

**gcpdiag** is a command-line diagnostics tool for GCP customers. It finds
and helps to fix common issues in Google Cloud Platform projects. It is used to
test projects against a wide range of best practices and frequent mistakes,
based on the troubleshooting experience of the Google Cloud Support team.

gcpdiag is open-source and contributions are welcome! Note that this is not
an officially supported Google product, but a community effort. The Google Cloud
Support team maintains this code and we do our best to avoid causing any
problems in your projects, but we give no guarantees to that end.

<img src="docs/gcpdiag-demo-2021-10-01.gif" alt="gcpdiag demo" width="800"/>

## Installation

You can run gcpdiag using a shell wrapper that starts gcpdiag in a Docker
container. This should work on any machine with Docker or Podman installed,
including Cloud Shell.

```
curl https://gcpdiag.dev/gcpdiag.sh >gcpdiag
chmod +x gcpdiag
./gcpdiag lint --project=MYPROJECT
```

## Usage

Currently gcpdiag mainly supports subcommand: `lint` and `Runbooks`, which is used
to run diagnostics on one or more GCP projects.

### LINT

```
usage:

gcpdiag lint --project P [OPTIONS]
gcpdiag lint --project P [--name faulty-vm --location us-central1-a --label key:value]

Run diagnostics in GCP projects.

optional arguments:
  -h, --help            show this help message and exit
  --auth-adc            Authenticate using Application Default Credentials (default)
  --auth-key FILE       Authenticate using a service account private key file
  --project P           Project ID of project to inspect
  --name n [n ...]      Resource Name(s) to inspect (e.g.: bastion-host,prod-*)
  --location R [R ...]  Valid GCP region/zone to scope inspection (e.g.: us-central1-a,us-central1)
  --label key:value     One or more resource labels as key-value pair(s) to scope inspection
                        (e.g.:  env:prod, type:frontend or env=prod type=frontend)
  --billing-project P   Project used for billing/quota of API calls done by gcpdiag (default is the inspected project, requires
                        'serviceusage.services.use' permission)
  --show-skipped        Show skipped rules
  --hide-ok             Hide rules with result OK
  --enable-gce-serial-buffer
                        Fetch serial port one output directly from the Compute API. Use this flag when not exporting
                        serial port output to cloud logging.
  --include INCLUDE     Include rule pattern (e.g.: `gke`, `gke/*/2021*`). Multiple pattern can be specified (comma separated, or with multiple
                        arguments)
  --exclude EXCLUDE     Exclude rule pattern (e.g.: `BP`, `*/*/2022*`)
  --include-extended    Include extended rules. Additional rules might generate false positives (default: False)
  -v, --verbose         Increase log verbosity
  --within-days D       How far back to search logs and metrics (default: 3 days)
  --config FILE         Read configuration from FILE
  --logging-ratelimit-requests R
                        Configure rate limit for logging queries (default: 60)
  --logging-ratelimit-period-seconds S
                        Configure rate limit period for logging queries (default: 60 seconds)
  --logging-page-size P
                        Configure page size for logging queries (default: 500)
  --logging-fetch-max-entries E
                        Configure max entries to fetch by logging queries (default: 10000)
  --logging-fetch-max-time-seconds S
                        Configure timeout for logging queries (default: 120 seconds)
  --output FORMATTER    Format output as one of [terminal, json, csv] (default: terminal)
```

#### RUNBOOK

```
usage:

gcpdiag runbook --project=project_id /name=instance_name [OPTIONS]

example:
gcpdiag runbook gce/ssh --project "project_id" -p "name=vm-id" -p "zone=us-central1-a"

optional arguments:
  -h, --help                              show this help message and exit
  --auth-adc                              Authenticate using Application Default Credentials
  --auth-key FILE                         Authenticate using a service account private key file
  --billing-project P                     Project used for billing/quota of API calls done by
                                          gcpdiag (default is the inspected project, requires 'serviceusage.services.use' permission)
  -v                                      Increase log verbosity

  Descriptions for Logging Options logging-related options:
  --logging-ratelimit-requests R`:        rate limit for API requests.
  --logging-ratelimit-period-seconds S`:  period in seconds for the API rate limit.
  --logging-page-size P`:                 page size for API requests.
  --logging-fetch-max-entries E`:         maximum number of entries to fetch.
  --logging-fetch-max-time-seconds S`:    maximum time in seconds to fetch logs.
```

## Further Information

See <http://gcpdiag.dev> for more information:

- [Documentation](https://gcpdiag.dev/docs/)
- [Lint rule description](https://gcpdiag.dev/rules/)
- [Runbook description](https://gcpdiag.dev/runbook/)
- [Development guides](https://gcpdiag.dev/docs/development/)

## Authentication

gcpdiag supports authentication using multiple mechanisms:

1. Application default credentials

   gcpdiag can use Cloud SDK's [Application Default
   Credentials](https://google-auth.readthedocs.io/en/latest/reference/google.auth.html#google.auth.default).
   This might require that you first run `gcloud auth login --update-adc` to
   update the cached credentials. This is the default in Cloud Shell because in
   that environment, ADC credentials are automatically provisioned.

1. Service account key

   You can also use the `--auth-key` parameter to specify the [private
   key](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)
   of a service account.

The authenticated principal will need as minimum the following roles granted (both of them):

- `Viewer` on the inspected project
- `Service Usage Consumer` on the project used for billing/quota enforcement,
  which is per default the project being inspected, but can be explicitly set
  using the `--billing-project` option

The Editor and Owner roles include all the required permissions, but if you use
service account authentication (`--auth-key`), we recommend to only grant the
Viewer+Service Usage Consumer on that service account.

## Test Products, Classes, and IDs

Tests are organized by product, class, and ID.

The **product** is the GCP service that is being tested. Examples: GKE or GCE.

The **class** is what kind of test it is, currently we have:

| Class name | Description                                     |
| ---------- | ----------------------------------------------- |
| BP         | Best practice, opinionated recommendations      |
| WARN       | Warnings: things that are possibly wrong        |
| ERR        | Errors: things that are very likely to be wrong |
| SEC        | Potential security issues                       |

The **ID** is currently formatted as YYYY_NNN, where YYYY is the year the test
was written, and NNN is a counter. The ID must be unique per product/class
combination.

Each test also has a **short_description** and a **long_description**. The short
description is a statement about the **good state** that is being verified to be
true (i.e. we don't test for errors, we test for compliance, i.e. an problem not
to be present).
