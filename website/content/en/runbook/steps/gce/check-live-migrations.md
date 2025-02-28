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

As remediation, you may try to simulate the migration (move the VM to another host) using
<https://cloud.google.com/compute/docs/instances/simulating-host-maintenance?hl=en#testingpolicies> ,
and see if issue still persists. If yes, please reach out to Google Cloud Platform Support teams via case.

Note: During live migration, VMs might experience a decrease in performance in disk,
CPU, memory, and network utilization for a short period of time
(<https://cloud.google.com/compute/docs/instances/live-migration-process#how_does_the_live_migration_process_work>).

### Success Reason

No live migrations detected for the VM during mentioned period

### Skipped Reason

There are no logs to examine !



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
