---
title: "gce/User Or Service Account Initiated Stop"
linkTitle: "User Or Service Account Initiated Stop"
weight: 3
type: docs
description: >
  Investigate the cause of a user-initiated VM termination
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step investigates whether the VM termination was initiated by a user or a system fault.

### Failure Reason

Account {stop_account} stopped the VM.

### Failure Remediation

Instance {full_resource_path} was intentionally stopped by account {stop_account}.

Simply restart the VM when safe to do so by following [1]

[1] <https://cloud.google.com/compute/docs/instances/stop-start-instance#restart-vm>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
