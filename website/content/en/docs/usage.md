---
title: "Usage information"
linkTitle: "Usage information"
weight: 4
description: >
    gcpdiag command-line usage
---
Currently gcpdiag mainly supports one subcommand: `lint`, which is used
to run diagnostics on one or more GCP projects.

```
usage: gcpdiag lint --project P [OPTIONS]
Run diagnostics in GCP projects.
optional arguments:
  -h, --help            show this help message and exit
  --auth-adc            Authenticate using Application Default Credentials
  --auth-key FILE       Authenticate using a service account private key file
  --auth-oauth          Authenticate using OAuth user authentication (default)
  --project P           Project ID of project to inspect
  --billing-project P   Project used for billing/quota of API calls done by gcpdiag (default is the inspected project, requires
                        'serviceusage.services.use' permission)
  --show-skipped        Show skipped rules
  --hide-ok             Hide rules with result OK
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
```
