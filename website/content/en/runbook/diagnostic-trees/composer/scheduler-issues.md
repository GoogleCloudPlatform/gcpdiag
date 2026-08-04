---
title: "composer/Scheduler Issues"
linkTitle: "composer/scheduler-issues"
weight: 3
type: docs
description: >
  Runbook for diagnosing Airflow Scheduler health issues.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)
**Kind**: Debugging Tree

### Description

This runbook investigates common causes for unhealthy Airflow schedulers:
  - High CPU utilization.
  - Missing deployments or deleted resources.
  - Service account issues.
  - Organization policy constraints.
  - Liveness probe failures.

### Executing this runbook

```shell
gcpdiag runbook composer/scheduler-issues \
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
| `start_time` | False | None | datetime | Start time for log analysis (YYYY-MM-DDTHH:MM:SSZ). |
| `end_time` | False | None | datetime | End time for log analysis (YYYY-MM-DDTHH:MM:SSZ). |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Scheduler Issues Start](/runbook/steps/composer/scheduler-issues-start)

  - [Scheduler Health Check](/runbook/steps/composer/scheduler-health-check)

  - [Scheduler Liveness Probe Check](/runbook/steps/composer/scheduler-liveness-probe-check)

  - [Scheduler Cpu Utilization](/runbook/steps/composer/scheduler-cpu-utilization)

  - [Check Scheduler Exceeded Runs](/runbook/steps/composer/check-scheduler-exceeded-runs)

  - [Check Deleted Airflow Scheduler Deployment](/runbook/steps/composer/check-deleted-airflow-scheduler-deployment)

  - [Disabled Environment Service Account](/runbook/steps/composer/disabled-environment-service-account)

  - [Deleted Environment Service Account](/runbook/steps/composer/deleted-environment-service-account)

  - [Shared Vpc Org Policy Constraint](/runbook/steps/composer/shared-vpc-org-policy-constraint)


<!--
This file is auto-generated. DO NOT EDIT.
-->
