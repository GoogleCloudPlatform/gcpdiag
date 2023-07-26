---
title: "Authentication"
linkTitle: "Authentication"
weight: 5
description: >
  Authentication mechanisms.
---

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

The credentials that you use with gcpdiag needs to have at minimum the
following roles granted (both of them):

- `Viewer` on the inspected project
- `Service Usage Consumer` on the project used for billing/quota enforcement,
  which is per default the project being inspected, but can be explicitely set
  using the `--billing-project` option

The Editor and Owner roles include all the required permissions, but we
recommend that if you use service account authentication (`--auth-key`), you
only grant the Viewer+Service Usage Consumer on that service account.
