---
title: "Usage information"
linkTitle: "Usage information"
weight: 4
description: >
    gcpdiag command-line usage
---

## Command Line Options

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

## Configuration File

The configuration for the gcpdiag run can be provided as a local configuration file via the `--config path/to/file` CLI flag written in YAML format.

If a value is provided on both the command line and via a configuration file, the values from the configuration file will be preferred.

### Example configuration which will be applied to any projects
```
---
billing_project: sample
include:
- '*BP*'
exclude:
- '*SEC*'
- '*ERR*'
include_extended: True
verbose: 3
within_days: 5
```

### Example configuration which will be applied to specific project
```
---
logging_fetch_max_time_seconds: 300
verbose: 3
within_days: 5

projects:
  myproject:
    billing_project: perproject
    include:
    - '*BP*'
    exclude:
    - '*SEC*'
    - '*ERR*'
    include_extended: True
```

If values are provided via a configuration file for any projects and specific project, the values from the configuration defined to specific project will be preferred.

> All values are supported (except `--project` and `-config`) and function identically to their CLI counterparts.
