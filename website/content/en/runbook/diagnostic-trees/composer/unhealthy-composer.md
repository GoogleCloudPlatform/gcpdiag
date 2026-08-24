---
title: "composer/Unhealthy Composer"
linkTitle: "composer/unhealthy-composer"
weight: 3
type: docs
description: >
  Diagnose and troubleshoot unhealthy Composer environments.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)
**Kind**: Debugging Tree

### Description

This runbook investigates common causes for an unhealthy status in a Cloud
  Composer environment by analyzing GKE health, resource utilization, and
  component logs.

  step 1 - Check environment health status
  step 2 - Check for GKE IP exhaustion
  step 3 - Validate environment service account status
  step 4 - Check plugins directory existence
  step 5 - Check web server CPU utilization
  step 6 - Check for monitoring pod restarts
  step 7 - Check for snapshot load pod restarts

### Executing this runbook

```shell
gcpdiag runbook composer/unhealthy-composer \
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
| `start_time` | True | None | datetime | The start time of the environment |
| `end_time` | True | None | datetime | The end time of the environment |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Unhealthy Composer Start](/runbook/steps/composer/unhealthy-composer-start)

  - [Monitoring Health Status](/runbook/steps/composer/monitoring-health-status)

  - [Gke Ip Exhaustion](/runbook/steps/composer/gke-ip-exhaustion)

  - [Service Account Status](/runbook/steps/composer/service-account-status)

  - [Plugins Directory Check](/runbook/steps/composer/plugins-directory-check)

  - [Web Server Cpu Utilization](/runbook/steps/composer/web-server-cpu-utilization)

  - [Monitoring Stability](/runbook/steps/composer/monitoring-stability)

  - [Snapshot Load Stability](/runbook/steps/composer/snapshot-load-stability)

  - [Unhealthy Composer End](/runbook/steps/composer/unhealthy-composer-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
