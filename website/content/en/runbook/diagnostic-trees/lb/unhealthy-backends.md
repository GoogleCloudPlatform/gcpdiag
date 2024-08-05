---
title: "lb/Unhealthy Backends"
linkTitle: "lb/unhealthy-backends"
weight: 3
type: docs
description: >
  Load Balancer Unhealthy Backends Analyzer.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)
**Kind**: Debugging Tree

### Description

This runbook helps investigate why backends in a load balancer are unhealthy.
  It confirms and summarizes the current health status of the backends, aiding
  in identifying any unhealthy instances.

  Key Investigation Areas:

  - Firewalls:
      - Verifies if firewall rules are properly configured to allow health check
      traffic.
  - Port Configuration:
      - Validates if the health check and serving ports are configured
      correctly, ensuring they are not mismatched.
  - Logging:
      - Checks if health check logging is enabled to aid in troubleshooting.
  - Health Check Logs (if enabled):
      - Analyzes the latest health check logs to identify the specific reasons
      for backend unhealthiness:
          - Timeouts: Identifies if the backend is timing out and provides
          potential causes and remediation steps.
          - Unhealthy: Indicates that the backend is reachable but doesn't meet
          the health check's criteria. It provides guidance on the expected
          health check behavior and suggests configuration checks.
          - Unknown: Explains the potential reasons for the "UNKNOWN" health
          state and suggests actions like adjusting timeouts or checking for
          Google Cloud outages.
  - Past Health Check Success:
      - Checks if the health check has worked successfully in the past to
      determine if the issue is recent or ongoing.

### Executing this runbook

```shell
gcpdiag runbook lb/unhealthy-backends \
  -p project_id=value \
  -p backend_service_name=value \
  -p region=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `backend_service_name` | True | None | str | The name of the backend service that you want to investigate |
| `region` | False | None | str | The region configured for the load balancer (backend service). If not provided, the backend service is assumed to be global. |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Unhealthy Backends Start](/runbook/steps/lb/unhealthy-backends-start)

  - [Verify Health Check Logging Enabled](/runbook/steps/lb/verify-health-check-logging-enabled)

  - [Analyze Latest Health Check Log](/runbook/steps/lb/analyze-latest-health-check-log)

  - [Check Past Health Check Success](/runbook/steps/lb/check-past-health-check-success)

  - [Validate Backend Service Port Configuration](/runbook/steps/lb/validate-backend-service-port-configuration)

  - [Verify Firewall Rules](/runbook/steps/lb/verify-firewall-rules)

  - [Unhealthy Backends End](/runbook/steps/lb/unhealthy-backends-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
