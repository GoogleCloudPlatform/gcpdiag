---
title: "gce/Ops Agent"
linkTitle: "gce/ops-agent"
weight: 3
type: docs
description: >
  Investigates the necessary GCP components for the proper functioning of the Ops Agent in a VM
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook will examine the following key areas:

  1. API Service Checks:
    - Ensures that Cloud APIs for Logging and/or Monitoring are accessible.

  2. Permission Checks:
    - Verifies that the necessary permissions are in place for exporting logs and/or metrics.

  3. Workload Authentication:
    - Confirms that the Ops Agent has a service account for authentication.
    - If using Google Application Credentials, provide the service account
      with the `gac_service_account` parameter.

  4. Scope of Investigation:
    - Note that this runbook does not include internal VM checks, such as guest OS investigations.

### Executing this runbook

```shell
gcpdiag runbook gce/ops-agent \
  -p project_id=value \
  -p name=value \
  -p id=value \
  -p zone=value \
  -p start_time=value \
  -p end_time=value \
  -p gac_service_account=value \
  -p check_logging=value \
  -p check_monitoring=value \
  -p check_serial_port_logging=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID containing the VM |
| `name` | False | None | str | Name of the GCE instance running the Ops Agent |
| `id` | False | None | str | ID of the GCE instance running the Ops Agent |
| `zone` | False | None | str | Zone of the GCE instance running the Ops Agent |
| `start_time` | False | None | datetime | Start time of the issue |
| `end_time` | False | None | datetime | End time of the issue |
| `gac_service_account` | False | None | str | GOOGLE_APPLICATION_CREDENTIALS used by ops agent, if applicable |
| `check_logging` | False | True | bool | Investigate logging issues |
| `check_monitoring` | False | True | bool | Investigate monitoring issues |
| `check_serial_port_logging` | False | True | bool | Check if VM Serial logging is enabled |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Ops Agent Start](/runbook/steps/gce/ops-agent-start)

  - [Vm Has A Service Account](/runbook/steps/gce/vm-has-a-service-account)

  - [Vm Has An Active Service Account](/runbook/steps/iam/vm-has-an-active-service-account)

  - [Investigate Logging Monitoring](/runbook/steps/gce/investigate-logging-monitoring)

  - [Service Api Status Check](/runbook/steps/gcp/service-api-status-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Vm Scope](/runbook/steps/gce/vm-scope)

  - [Vm Has Ops Agent](/runbook/steps/gce/vm-has-ops-agent)

  - [Check Serial Port Logging](/runbook/steps/gce/check-serial-port-logging)

  - [Service Api Status Check](/runbook/steps/gcp/service-api-status-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Vm Scope](/runbook/steps/gce/vm-scope)

  - [Vm Has Ops Agent](/runbook/steps/gce/vm-has-ops-agent)

  - [Ops Agent End](/runbook/steps/gce/ops-agent-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
