---
title: "composer/Runbook Airflow Worker Restart"
linkTitle: "composer/runbook-airflow-worker-restart"
weight: 3
type: docs
description: >
  Runbook addresses the root causes of Airflow worker instability.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)
**Kind**: Debugging Tree

### Description

This runbook checks for the following:
  - Verify Composer environment exists and find the associated GKE cluster
  - Check for OOMKilled Events in Logs
  - Check for SIGKILL / Zombie Tasks
  - Check for Ephemeral Storage Exhaustion
  - Check for gcs-syncd Ephemeral Storage Limit Issue
  - Check for Worker Liveness Probe Logs.
  - Check for Unschedulable Pods

### Executing this runbook

```shell
gcpdiag runbook composer/runbook-airflow-worker-restart \
  -p project_id=value \
  -p name=value \
  -p start_time=value \
  -p end_time=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `name` | True | None | str | The name of the Composer environment |
| `start_time` | True | None | datetime | The start time of the investigation |
| `end_time` | True | None | datetime | The end time of the investigation |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Worker Restart Start](/runbook/steps/composer/worker-restart-start)

  - [Infrastructure Checks](/runbook/steps/composer/infrastructure-checks)

  - [Check Liveness Probes](/runbook/steps/composer/check-liveness-probes)

  - [Check Scheduling Failures](/runbook/steps/composer/check-scheduling-failures)

  - [Check Gke Preemption](/runbook/steps/composer/check-gke-preemption)

  - [Check Worker Oom](/runbook/steps/composer/check-worker-oom)

  - [Check Zombie Tasks](/runbook/steps/composer/check-zombie-tasks)

  - [Check Ephemeral Storage](/runbook/steps/composer/check-ephemeral-storage)

  - [Check Gcs Syncd Ephemeral Storage Limit](/runbook/steps/composer/check-gcs-syncd-ephemeral-storage-limit)

  - [Runbook Airflow Worker Restart End](/runbook/steps/composer/runbook-airflow-worker-restart-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
