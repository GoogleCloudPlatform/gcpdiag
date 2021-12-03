---
title: "Running gcpdiag"
linkTitle: "Running gcpdiag"
weight: 3
description: >
  Prerequisites and how run gcpdiag.
---

## Pre-requisites

gcpdiag requires the following in order to be able to run correctly:

#### 1. Permissions

The credentials that you use with gcpdiag needs to have at minimum the
following roles granted (both of them):

- `Viewer` on the inspected project
- `Service Usage Consumer` on the project used for billing/quota enforcement,
  which is per default the project being inspected, but can be explicitely set
  using the `--billing-project` option

The Editor and Owner roles include all the required permissions, but we
recommend that if you use service account authentication (`--auth-key`), you
only grant the Viewer+Service Usage Consumer on that service account.

#### 2. Cloud Resource Manager API

You need the **Cloud Resource Manager API** to be enabled on the GCP project you
are trying to diagnose. You can either enable it from the
[GCP console](https://console.cloud.google.com/marketplace/product/google/cloudresourcemanager.googleapis.com)
or use the `gcloud` CLI.

```
gcloud --project=MYPROJECT services enable \
    cloudresourcemanager.googleapis.com
```

## Running with Docker

You can run gcpdiag using a shell wrapper that starts gcpdiag in a Docker
container. This should work on any machine with Docker or Podman installed,
including Cloud Shell.

```
curl https://gcpdiag.dev/gcpdiag.sh >gcpdiag
chmod +x gcpdiag
./gcpdiag lint --project=MYPROJECT
```
