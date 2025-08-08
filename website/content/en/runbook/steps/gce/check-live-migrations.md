---
title: "gce/Check Live Migrations"
linkTitle: "Check Live Migrations"
weight: 3
type: docs
description: >
  Checking if live migrations happened for the instance
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Live migrations detected for the VM during mentioned period.

### Failure Remediation

Simulate the migration (move the VM to another host) using the guidance provided here:
<https://cloud.google.com/compute/docs/instances/simulating-host-maintenance?hl=en#testingpolicies>
Verify if the issue persists after simulation. If it does, contact Google Cloud Platform Support by creating a support case.

Note: During live migration, VMs might experience a temporary decrease in performance (disk, CPU, memory, network). See the documentation for details:
<https://cloud.google.com/compute/docs/instances/live-migration-process#how_does_the_live_migration_process_work>

### Success Reason

No live migrations detected for the VM during mentioned period

### Skipped Reason

There are no logs to examine !



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
