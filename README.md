# gcpdiag - Diagnostics for Google Cloud Platform

[![code analysis badge](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/code-analysis.yml/badge.svg?branch=main&event=push)](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/code-analysis.yml?query=branch%3Amain+event%3Apush)
[![test badge](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)

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
container. This should work on any machine with Docker installed, including
Cloud Shell.

```
curl https://gcpdiag.dev/gcpdiag.sh >gcpdiag
chmod +x gcpdiag
gcloud auth login --update-adc
./gcpdiag lint --project=MYPROJECT
```

Note: the `gcloud auth` step is not required in Cloud Shell.

## Usage

Currently gcpdiag mainly supports one subcommand: `lint`, which is used
to run diagnostics on one or more GCP projects.

```
usage: gcpdiag lint --project P [OPTIONS]

Run diagnostics in GCP projects.

optional arguments:
  -h, --help           show this help message and exit
  --auth-adc           Authenticate using Application Default Credentials
  --auth-key FILE      Authenticate using a service account private key file
  --auth-oauth         Authenticate using OAuth user authentication
  --project P          Project ID of project to inspect
  --billing-project P  Project used for billing/quota of API calls done by gcpdiag
                       (default is the inspected project, requires 'serviceusage.services.use' permission)
  --show-skipped       Show skipped rules
  --hide-ok            Hide rules with result OK
  --include INCLUDE    Include rule pattern (e.g.: `gke`, `gke/*/2021*`). Multiple pattern can be specified
                       (comma separated, or with multiple arguments)
  --exclude EXCLUDE    Exclude rule pattern (e.g.: `BP`, `*/*/2022*`)
  -v, --verbose        Increase log verbosity
  --within-days D      How far back to search logs and metrics (default: 3)
```

### Authentication

gcpdiag supports authentication using multiple mechanisms:

1. Application default credentials

   gcpdiag uses by default [Application Default
   Credentials](https://google-auth.readthedocs.io/en/latest/reference/google.auth.html#google.auth.default).
   This might require that you first run `gcloud auth login --update-adc` to
   update the cached credentials.

1. OAuth user consent flow

   gcpdiag can use a OAuth user authentication flow, similarly to what gcloud
   does. It will print a URL that you need to access with a browser, and ask you
   to enter the token that you receive after you authenticate there.

   The credentials will be cached on disk, so that you can keep running it for 1
   hour. To remove cached authentication credentials, you can delete the
   `$HOME/.cache/gcpdiag` directory.

   **Note**: OAuth-based authentication is currently not working for users
   outside of the `google.com` domain, because gcpdiag is not approved for
   external OAuth authentication yet.

1. Service account key

   You can also use the `--auth-key` parameter to specify the [private
   key](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)
   of a service account.

The authenticated user will need as minimum the following roles granted (both of them):

- `Viewer` on the inspected project
- `Service Usage Consumer` on the project used for billing/quota enforcement,
  which is per default the project being inspected, but can be explicitely set
  using the `--billing-project` option

The Editor and Owner roles include all the required permissions, but we
recommend that if you use service account authentication (`--auth-key`), you
only grant the Viewer+Service Usage Consumer on that service account.

### Test Products, Classes, and IDs

Tests are organized by product, class, and ID.

The **product** is the GCP service that is being tested. Examples: GKE or GCE.

The **class** is what kind of test it is, currently we have:

Class name | Description
---------- | -----------------------------------------------
BP         | Best practice, opinionated recommendations
WARN       | Warnings: things that are possibly wrong
ERR        | Errors: things that are very likely to be wrong
SEC        | Potential security issues

The **ID** is currently formatted as YYYY_NNN, where YYYY is the year the test
was written, and NNN is a counter. The ID must be unique per product/class
combination.

Each test also has a **short_description** and a **long_description**. The short
description is a statement about the **good state** that is being verified to be
true (i.e. we don't test for errors, we test for compliance, i.e. an problem not
to be present).

## Further Information

See http://gcpdiag.dev for more information:

- <a href="https://gcpdiag.dev/docs/">Documentation</a>
- <a href="https://gcpdiag.dev/rules/">Lint rule descriptions</a>
- <a href="https://gcpdiag.dev/docs/development/">Development guides</a>
