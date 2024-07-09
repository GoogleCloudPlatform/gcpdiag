---
title: "dataproc/Cluster Creation"
linkTitle: "dataproc/cluster-creation"
weight: 3
type: docs
description: >
  Provides a comprehensive analysis of common issues which affects Dataproc cluster creation.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)
**Kind**: Debugging Tree

### Description

This runbook focuses on a range of potential problems for Dataproc clusters on
  Google Cloud Platform. By conducting a series of checks, the runbook aims to
  pinpoint the root cause of cluster creation difficulties.

  The following areas are examined:

  - Stockout errors: Evaluates Logs Explorer logs regarding stockout in the
  region/zone.

  - Quota availibility: Checks for the quota availibility in Dataproc cluster project.

  - Network configuration: Performs GCE Network Connectivity Tests, checks necessary firewall rules, external/internal IP configuration.

  - Cross-project configuration: Checks if the service account is not in the same
  project and reviews additional
    roles and organization policies enforcement.

  - Shared VPC configuration: Checks if the Dataproc cluster uses a Shared VPC network and
  evaluates if right service account roles are added.

  - Init actions script failures: Evaluates Logs Explorer
  logs regarding init actions script failures or timeouts.

### Executing this runbook

```shell
gcpdiag runbook dataproc/cluster-creation \
  -p project_id=value \
  -p cluster_name=value \
  -p cluster_uuid=value \
  -p project_number=value \
  -p service_account=value \
  -p constraint=value \
  -p stackdriver=value \
  -p region=value \
  -p zone=value \
  -p network=value \
  -p subnetwork=value \
  -p internal_ip_only=value \
  -p start_time_utc=value \
  -p end_time_utc=value \
  -p cross_project=value \
  -p host_vpc_project=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID where the Dataproc cluster is located |
| `cluster_name` | True | None | str | Dataproc cluster Name of an existing/active resource |
| `cluster_uuid` | False | None | str | Dataproc cluster UUID |
| `project_number` | False | None | str | The Project Number where the Dataproc cluster is located |
| `service_account` | False | None | str | Dataproc cluster Service Account used to create the resource |
| `constraint` | False | None | bool | Checks if the Dataproc cluster has an enforced organization policy constraint |
| `stackdriver` | False | True | str | Checks if stackdriver logging is enabled for further troubleshooting |
| `region` | False | None | str | Dataproc cluster Region |
| `zone` | False | None | str | Dataproc cluster Zone |
| `network` | False | None | str | Dataproc cluster Network |
| `subnetwork` | False | None | str | Dataproc cluster Subnetwork |
| `internal_ip_only` | False | None | bool | Checks if the Dataproc cluster has been created with only Internal IP |
| `start_time_utc` | False | None | datetime | Start time of the issue |
| `end_time_utc` | False | None | datetime | End time of the issue |
| `cross_project` | False | None | str | Cross Project ID, where service account is located if it is not in the same project as the Dataproc cluster |
| `host_vpc_project` | False | None | str | Project ID of the Shared VPC network |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Check Cluster Quota](/runbook/steps/dataproc/check-cluster-quota)

  - [Check Cluster Stock Out](/runbook/steps/dataproc/check-cluster-stock-out)

  - [Cluster Creation End](/runbook/steps/dataproc/cluster-creation-end)

  - [Cluster Exists](/runbook/steps/dataproc/cluster-exists)

  - [Cluster Creation End](/runbook/steps/dataproc/cluster-creation-end)

  - [Cluster In Error](/runbook/steps/dataproc/cluster-in-error)

  - [Cluster Details](/runbook/steps/dataproc/cluster-details)

  - [Cluster Details](/runbook/steps/dataproc/cluster-details)

  - [Cluster Creation End](/runbook/steps/dataproc/cluster-creation-end)

  - [Check Cluster Network](/runbook/steps/dataproc/check-cluster-network)

  - [Internal Ip Gateway](/runbook/steps/dataproc/internal-ip-gateway)

  - [Check Private Google Access](/runbook/steps/dataproc/check-private-google-access)

  - [Service Account Exists](/runbook/steps/dataproc/service-account-exists)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Org Policy Check](/runbook/steps/crm/org-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Check Shared V P C Roles](/runbook/steps/dataproc/check-shared-v-p-c-roles)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Check Init Script Failure](/runbook/steps/dataproc/check-init-script-failure)

  - [Cluster Creation End](/runbook/steps/dataproc/cluster-creation-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
