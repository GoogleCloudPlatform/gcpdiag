---
title: "gke/Monitoring Configuration"
linkTitle: "gke/monitoring-configuration"
weight: 3
type: docs
description: >
  Verifies that GKE Monitoring and its components are correctly configured and operational.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook guides through a systematic investigation of potential
  causes when monitoring from the Google Kubernetes Engine (GKE) cluster are missing
  or incomplete. The focus is on core configuration settings that are essential
  for proper monitoring functionality.

  The following areas are examined:

  - **Project-Level Monitoring:** Ensures that the Google Cloud project housing
  the GKE cluster has the Cloud Monitoring API enabled.

  - **Cluster-Level Monitoring:** Verifies that monitoring is explicitly enabled
  within the GKE cluster's configuration.

  - **Node Pool Permissions:** Confirms that the nodes within the cluster's
  node pools have the 'Cloud Monitoring Write' scope enabled, allowing them to send
  metrics data.

  - **Service Account Permissions:** Validates that the service account used
  by the node pools possesses the necessary IAM permissions to interact with
  Cloud Monitoring. Specifically, the "roles/monitoring.metricWriter" role is typically
  required.

### Executing this runbook

```shell
gcpdiag runbook gke/monitoring-configuration \
  -p project_id=value \
  -p gke_cluster_name=value \
  -p location=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GKE Cluster |
| `gke_cluster_name` | True | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `location` | True | None | str | The zone or region of the GKE cluster |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Monitoring Configuration Start](/runbook/steps/gke/monitoring-configuration-start)

  - [Monitoring Api Configuration Enabled](/runbook/steps/gke/monitoring-api-configuration-enabled)

  - [Cluster Level Monitoring Configuration Enabled](/runbook/steps/gke/cluster-level-monitoring-configuration-enabled)

  - [Node Pool Cloud Monitoring Access Scope Configuration](/runbook/steps/gke/node-pool-cloud-monitoring-access-scope-configuration)

  - [Service Account Monitoring Permission Configuration](/runbook/steps/gke/service-account-monitoring-permission-configuration)

  - [Monitoring Configuration End](/runbook/steps/gke/monitoring-configuration-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
