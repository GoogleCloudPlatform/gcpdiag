# gcp-doctor - Diagnostics for Google Cloud Platform

**gcp-doctor** is a command-line diagnostics tool for GCP customers. It finds
and helps to fix common issues in Google Cloud Platform projects. It is used to
test projects against a wide range of best-practices and frequent mistakes,
based on the troubleshooting experience of the Google Cloud Support team.

gcp-doctor is open-source and contributions are welcome! Note that this is not
an officially supported Google Cloud product, but a community effort. The Google
Cloud Support team maintains this code and we do our best to avoid causing any
problems in your projects, but we give no guarantees to that end.

## Running gcp-doctor

You can run gcp-doctor using a shell wrapper that starts gcp-doctor in a Docker
container. This should work on any machine with Docker installed, including
Cloud Shell.

```
curl https://storage.googleapis.com/gcp-doctor/gcp-doctor.sh >gcp-doctor
chmod +x gcp-doctor
./gcp-doctor lint --project=[*MYPROJECT*]
```

We recommend that you put the wrapper script in a directory that is already in
your PATH, so that you can run it from anywhere.

### Authentication

gcp-doctor uses the GCP public APIs and needs credentials to access your GCP
projects. The first time that you run it, it will ask you to authenticate with
your browser, similarly to what gcloud does. The credentials will be cached on
disk, so that you can keep running it for 1 hour.

To remove cached authentication credentials, you can delete the
`$HOME/.cache/gcp-doctor` directory.

### Usage

```
usage: gcp-doctor lint --project P [OPTIONS]

Run diagnostics in GCP projects.

optional arguments:
  -h, --help      show this help message and exit
  --project P     Project ID (can be specified multiple times)
  --show-skipped  Show skipped rules
  --hide-ok       Hide rules with result OK
  -v, --verbose   Increase log verbosity
```

## Test Products, Classes, and IDs

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
