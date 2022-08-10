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
  --auth-adc            Authenticate using Application Default Credentials (default)
  --auth-key FILE       Authenticate using a service account private key file
  --auth-oauth          Authenticate using OAuth user authentication (currently marked as deprecated, consider using other authentication methods)
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
  --output FORMATTER    Format output as one of [terminal, json, csv] (default: terminal)
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

## Output formats

The output format for the gcpdiag run can be configured via `--output formatter` CLI flag, where `formatter` can be one of the following options:
- `terminal` - which is default output format designed to be human readable
- `json` - can be helpful as a machine readable format used for example with CI/CD pipelines
- `csv` - can be helpful as a machine readable format used for example with analytic tools

Final report can be easily streamed to file by using file redirection. Result will contain only a report of the lint execution with configured output format.

For example:
```
gcpdiag lint --project example-project --output csv > gcpdiag.report.csv
```

will generate file `gcpdiag.report.csv` with following content:
```
rule,resource,status,message,doc_url
gcs/BP/2022_001,b/example-project/artifacts.example-project.appspot.com,FAIL,it is recommend to use uniform access on your bucket,https://gcpdiag.dev/rules/gcs/BP/2022_001
gcs/BP/2022_001,b/example-project/example-project.appspot.com,FAIL,it is recommend to use uniform access on your bucket,https://gcpdiag.dev/rules/gcs/BP/2022_001
gcs/BP/2022_001,b/example-project/staging.example-project.appspot.com,FAIL,it is recommend to use uniform access on your bucket,https://gcpdiag.dev/rules/gcs/BP/2022_001
iam/SEC/2021_001,projects/example-project,OK,-,https://gcpdiag.dev/rules/iam/SEC/2021_001
```

> Value can be also provided as a yaml configuration file via the `--config path/to/file` CLI flag.

### Example of the terminal (default) output format

```
gcpdiag 🩺 0.54-test

Starting lint inspection (project: example-project)...

🔎 gcs/BP/2022_001: Buckets are using uniform access
   - example-project/artifacts.example-project.appspot.com        [FAIL]
     it is recommend to use uniform access on your bucket
   - example-project/example-project.appspot.com                  [FAIL]
     it is recommend to use uniform access on your bucket
   - example-project/staging.example-project.appspot.com          [FAIL]
     it is recommend to use uniform access on your bucket

   Google recommends using uniform access for a Cloud Storage bucket IAM policy
   https://cloud.google.com/storage/docs/access-
   control#choose_between_uniform_and_fine-grained_access

   https://gcpdiag.dev/rules/gcs/BP/2022_001

🔎 iam/SEC/2021_001: No service accounts have the Owner role
   - example-project                                                  [ OK ]

Rules summary: 64 skipped, 1 ok, 1 failed
How good were the results? https://forms.gle/jG1dUdkxhP2s5ced6
```
### Example of the json output format

```
gcpdiag 0.54-test

Starting lint inspection (project: example-project)...

[
{
  "rule": "gcs/BP/2022_001",
  "resource": "b/artifacts.example-project.appspot.com",
  "status": "FAIL",
  "message": "it is recommend to use uniform access on your bucket",
  "doc_url": "https://gcpdiag.dev/rules/gcs/BP/2022_001"
},
{
  "rule": "gcs/BP/2022_001",
  "resource": "b/example-project.appspot.com",
  "status": "FAIL",
  "message": "it is recommend to use uniform access on your bucket",
  "doc_url": "https://gcpdiag.dev/rules/gcs/BP/2022_001"
},
{
  "rule": "gcs/BP/2022_001",
  "resource": "b/staging.example-project.appspot.com",
  "status": "FAIL",
  "message": "it is recommend to use uniform access on your bucket",
  "doc_url": "https://gcpdiag.dev/rules/gcs/BP/2022_001"
},
{
  "rule": "iam/SEC/2021_001",
  "resource": "projects/example-project",
  "status": "OK",
  "message": "-",
  "doc_url": "https://gcpdiag.dev/rules/iam/SEC/2021_001"
},
]

Rules summary: 64 skipped, 1 ok, 1 failed
How good were the results? https://forms.gle/jG1dUdkxhP2s5ced6
```

### Example of the csv output format

```
gcpdiag 0.54-test

Starting lint inspection (project: example-project)...

rule,resource,status,message,doc_url
gcs/BP/2022_001,b/artifacts.example-project.appspot.com,FAIL,it is recommend to use uniform access on your bucket,https://gcpdiag.dev/rules/gcs/BP/2022_001
gcs/BP/2022_001,b/example-project.appspot.com,FAIL,it is recommend to use uniform access on your bucket,https://gcpdiag.dev/rules/gcs/BP/2022_001
gcs/BP/2022_001,b/staging.example-project.appspot.com,FAIL,it is recommend to use uniform access on your bucket,https://gcpdiag.dev/rules/gcs/BP/2022_001
iam/SEC/2021_001,projects/example-project,OK,-,https://gcpdiag.dev/rules/iam/SEC/2021_001

Rules summary: 64 skipped, 1 ok, 1 failed
How good were the results? https://forms.gle/jG1dUdkxhP2s5ced6
```
