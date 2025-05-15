---
title: "gce/Terminate On Host Maintenance"
linkTitle: "Terminate On Host Maintenance"
weight: 3
type: docs
description: >
  Investigate the cause of termination related to host maintenance
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

Termination on host maintenance is normal behavior. This step verifies if it was expected.
  This will typically happen during a failed live migration.

### Failure Reason

{status_message}

### Failure Remediation

Instance {full_resource_path} maintenance policy is set to TERMINATE, Compute Engine
stops your VM when there is a maintenance event where Google must move your VM to another host.

If you want to change your VM's onHostMaintenance policy to restart automatically
or live migrate [1]. Read more about Host Events [2] and how to set your termination policies[3].

[1] <https://cloud.google.com/compute/docs/instances/live-migration-process>
[2] <https://cloud.google.com/compute/docs/instances/setting-vm-host-options>
[3] <https://cloud.google.com/compute/docs/instances/host-maintenance-overview>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
