---
title: "lb/Latency"
linkTitle: "lb/latency"
weight: 3
type: docs
description: >
  This runbook diagnoses and troubleshoots latency issues with Application Load Balancers.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)
**Kind**: Debugging Tree

### Description

It analyzes key metrics to identify potential bottlenecks and performance
  problems.

  Key Investigation Areas:

  - Backend Latency:
    - Measures the time taken for backends to respond to requests, checking if
    it exceeds a configurable threshold.
  - Request Count Per Second (QPS):
    - Monitors the rate of incoming requests to the load balancer, checking if
    it exceeds a configurable threshold.  A high request count coupled with high
    latency might suggest overload.
  - 5xx Error Rate:
    - Calculates the percentage of 5xx server errors, indicating problems on the
    backend servers.  This check uses a configurable threshold and considers the
    request count to provide a meaningful error rate.

### Executing this runbook

```shell
gcpdiag runbook lb/latency \
  -p project_id=value \
  -p forwarding_rule_name=value \
  -p region=value \
  -p backend_latency_threshold=value \
  -p request_count_threshold=value \
  -p error_rate_threshold=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID where the load balancer is located |
| `forwarding_rule_name` | True | None | str | The name of the forwarding rule associated with the Load Balancer to check |
| `region` | False | None | str | The region where the forwarding rule is located |
| `backend_latency_threshold` | False | None | float | Threshold for backend latency in milliseconds. |
| `request_count_threshold` | False | None | float | Threshold for average request count per second. |
| `error_rate_threshold` | False | None | float | Threshold for error rate (percentage of 5xx errors). |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Lb Latency Start](/runbook/steps/lb/lb-latency-start)

  - [Lb Backend Latency Check](/runbook/steps/lb/lb-backend-latency-check)

  - [Lb Request Count Check](/runbook/steps/lb/lb-request-count-check)

  - [Lb Error Rate Check](/runbook/steps/lb/lb-error-rate-check)

  - [Latency End](/runbook/steps/lb/latency-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
