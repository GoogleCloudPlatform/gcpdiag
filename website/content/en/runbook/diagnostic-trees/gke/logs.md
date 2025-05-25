---
title: "gke/Logs"
linkTitle: "gke/logs"
weight: 3
type: docs
description: >
  Provides a methodical approach to troubleshooting GKE logging issues.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook guides you through a systematic investigation of potential
  causes when logs from the Google Kubernetes Engine (GKE) cluster are missing
  or incomplete. The focus is on core configuration settings that are essential
  for proper logging functionality.

  The following areas are examined:

  - **Project-Level Logging:** Ensures that the Google Cloud project housing
  the GKE cluster has the Cloud Logging API enabled.

  - **Cluster-Level Logging:** Verifies that logging is explicitly enabled
  within the GKE cluster's configuration.

  - **Node Pool Permissions:** Confirms that the nodes within the cluster's
  node pools have the 'Cloud Logging Write' scope enabled, allowing them to send
  log data.

  - **Service Account Permissions:** Validates that the service account used
  by the node pools possesses the necessary IAM permissions to interact with
  Cloud Logging. Specifically, the "roles/logging.logWriter" role is typically
  required.

  - **Cloud Logging API Write Quotas:** Verifies that Cloud Logging API Write
  quotas have not been exceeded within the specified timeframe.

### Executing this runbook

```shell
gcpdiag runbook gke/logs \
  -p project_id=value \
  -p name=value \
  -p gke_cluster_name=value \
  -p location=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GKE Cluster |
| `name` | False | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `gke_cluster_name` | True | None | str | The name of the GKE cluster |
| `location` | True | None | str | The zone or region of the GKE cluster |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Logs Start](/runbook/steps/gke/logs-start)

  - [Logging Api Enabled](/runbook/steps/gke/logging-api-enabled)

  - [Cluster Level Logging Enabled](/runbook/steps/gke/cluster-level-logging-enabled)

  - [Node Pool Cloud Logging Access Scope](/runbook/steps/gke/node-pool-cloud-logging-access-scope)

  - [Service Account Logging Permission](/runbook/steps/gke/service-account-logging-permission)

  - [Logging Write Api Quota Exceeded](/runbook/steps/gke/logging-write-api-quota-exceeded)

  - [Logs End](/runbook/steps/gke/logs-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
