---
title: "composer/Redis Troubleshooting"
linkTitle: "composer/redis-troubleshooting"
weight: 3
type: docs
description: >
  Runbook for troubleshooting Redis.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)
**Kind**: Debugging Tree

### Description

- Redis OOM (Memory Exhaustion)
  - Failure to authenticate due to Invalid Password
  - Firewall rules blocking Redis traffic
  - Check Celery broker publishing timeouts

### Executing this runbook

```shell
gcpdiag runbook composer/redis-troubleshooting \
  -p project_id=value \
  -p name=value \
  -p start_time=value \
  -p end_time=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `name` | True | None | str | The name of the Cloud Composer environment |
| `start_time` | False | None | datetime | The start time of the time range to query logs. |
| `end_time` | False | None | datetime | The end time of the time range to query logs. |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Redis Troubleshooting Start](/runbook/steps/composer/redis-troubleshooting-start)

  - [Check Redis Oom](/runbook/steps/composer/check-redis-oom)

  - [Check Redis Oom Node](/runbook/steps/composer/check-redis-oom-node)

  - [Check Auth](/runbook/steps/composer/check-auth)

  - [Check Firewall](/runbook/steps/composer/check-firewall)

  - [Check Celery Broker Publishing Timeouts](/runbook/steps/composer/check-celery-broker-publishing-timeouts)

  - [Redis End](/runbook/steps/composer/redis-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
