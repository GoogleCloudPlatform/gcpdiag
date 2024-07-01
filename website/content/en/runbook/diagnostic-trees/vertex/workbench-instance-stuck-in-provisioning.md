---
title: "vertex/Workbench Instance Stuck In Provisioning"
linkTitle: "vertex/workbench-instance-stuck-in-provisioning"
weight: 3
type: docs
description: >
  Runbook to Troubleshoot Issue: Vertex AI Workbench Instance Stuck in Provisioning State
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)
**Kind**: Debugging Tree

### Description

This runbook investigates root causes for the Workbench Instance to be stuck in provisioning state

  Areas Examined:

  - Workbench Instance State: Checks the instance's current state ensuring that it is
    stuck in provisioning status and not stopped or active.

  - Workbench Instance Compute Engine VM Boot Disk Image: Checks if the instance has been created
    with a custom container, the official 'workbench-instances' images, deep learning VMs images,
    or unsupported images that might cause the instance to be stuck in provisioning state.

  - Workbench Instance Custom Scripts: Checks if the instance is not using custom scripts that may
    affect the default configuration of the instance by changing the Jupyter port or breaking
    dependencies that might cause the instance to be stuck in provisioning state.

  - Workbench Instance Environment Version: Checks if the instance is using the latest environment
    version by checking its upgradability. Old versions sometimes are the root cause for the
    instance to be stuck in provisioning state.

  - Workbench Instance Compute Engine VM Performance: Checks the VM's current performance, ensuring
    that it is not impaired by high CPU usage, insufficient memory, or disk space issues that might
    disrupt normal operations.

  - Workbench Instance Compute Engine Serial Port Logging: Checks if the instance has serial port
    logs which can be analyzed to ensure Jupyter is running on port 127.0.0.1:8080
    which is mandatory.

  - Workbench Instance Compute Engine SSH and Terminal access: Checks if the instance's
    compute engine vm is running so the user can ssh and open a terminal to check for space
    usage in 'home/jupyter'. If no space is left, that may cause the instance to be stuck
    in provisioning state.

  - Workbench Instance External IP Disabled: Checks if the external IP disabled. Wrong networking
    configurations may cause the instance to be stuck in provisioning state.

### Executing this runbook

```shell
gcpdiag runbook vertex/workbench-instance-stuck-in-provisioning \
  -p project_id=value \
  -p instance_name=value \
  -p zone=value \
  -p start_time_utc=value \
  -p end_time_utc=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `instance_name` | True |  | str | Name of the Workbench Instance |
| `zone` | True | us-central1-a | str | Zone of the Workbench Instance. e.g. us-central1-a |
| `start_time_utc` | False | None | datetime | Start time of the issue |
| `end_time_utc` | False | None | datetime | End time of the issue |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Workbench Instance Stuck In Provisioning Start](/runbook/steps/vertex/workbench-instance-stuck-in-provisioning-start)

  - [Check Workbench Instance Using Custom Container](/runbook/steps/vertex/check-workbench-instance-using-custom-container)

  - [Check Workbench Instance Using Official Image](/runbook/steps/vertex/check-workbench-instance-using-official-image)

  - [Check Workbench Instance Custom Scripts](/runbook/steps/vertex/check-workbench-instance-custom-scripts)

  - [Check Workbench Instance Is Using Latest Env Version](/runbook/steps/vertex/check-workbench-instance-is-using-latest-env-version)

  - [Check Workbench Instance Performance](/runbook/steps/vertex/check-workbench-instance-performance)

  - [High Vm Memory Utilization](/runbook/steps/gce/high-vm-memory-utilization)

  - [High Vm Disk Utilization](/runbook/steps/gce/high-vm-disk-utilization)

  - [High Vm Cpu Utilization](/runbook/steps/gce/high-vm-cpu-utilization)

  - [Decision Check Workbench Instance System Logging](/runbook/steps/vertex/decision-check-workbench-instance-system-logging)

  - [Check Workbench Instance Syslogs Jupyter Running On Port8080](/runbook/steps/vertex/check-workbench-instance-syslogs-jupyter-running-on-port8080)

  - [Check Workbench Instance Compute Engine S S H](/runbook/steps/vertex/check-workbench-instance-compute-engine-s-s-h)

  - [Check Workbench Instance Jupyter Space](/runbook/steps/vertex/check-workbench-instance-jupyter-space)

  - [Check Workbench Instance External Ip Disabled](/runbook/steps/vertex/check-workbench-instance-external-ip-disabled)

  - [Workbench Instance Stuck In Provisioning End](/runbook/steps/vertex/workbench-instance-stuck-in-provisioning-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
