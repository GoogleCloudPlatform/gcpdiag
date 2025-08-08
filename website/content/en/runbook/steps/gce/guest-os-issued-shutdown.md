---
title: "gce/Guest Os Issued Shutdown"
linkTitle: "Guest Os Issued Shutdown"
weight: 3
type: docs
description: >
  Investigate shutdowns issued from within the guest OS
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step investigates whether the VM termination was initiated by a user or a system fault
  within the guest OS. It provides insights into the root cause of the termination.

### Failure Reason

{status_message}

### Failure Remediation

Instance {full_resource_path} shutdown was initiated from the operating system.

This is usually caused by a sudoer posix user issuing a shutdown or reboot command
Review guest shell history to determine who or what application triggered the shutdown.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
