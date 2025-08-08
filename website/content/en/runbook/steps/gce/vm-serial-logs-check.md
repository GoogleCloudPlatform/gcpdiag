---
title: "gce/Vm Serial Logs Check"
linkTitle: "Vm Serial Logs Check"
weight: 3
type: docs
description: >
  Searches for predefined good or bad patterns in the serial logs of a GCE Instance.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This diagnostic step checks the VM's serial logs for patterns that are indicative of successful
  operations ('GOOD_PATTERN') or potential issues ('BAD_PATTERN'). Based on the presence of these
  patterns, the step categorizes the VM's status as 'OK', 'Failed', or 'Uncertain'.

### Failure Reason

Anomalies detected in the serial logs which align with the investigated bad patterns

### Failure Remediation

Investigate potential issues via the serial console.
If GRUB_TIMEOUT is greater than 0, access the interactive session for more insights.
Explore rescue options for inaccessible VMs or review possible guest OS issues.

- Interactive Serial Console: <https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-using-serial-console>
- Rescuing VMs: <https://cloud.google.com/compute/docs/troubleshooting/rescue-vm>

If escalating Guest OS related issues to Google Cloud Support,
verify that the issue is in line with Google Cloud Platform's Guest OS support policy

- Google Cloud Platform Support Scope:
<https://cloud.google.com/compute/docs/images/support-maintenance-policy#support-scope>

### Success Reason

The VM's Linux OS shows no signs of anomalies,
indicating a *likely* stable operational state.

### Uncertain Reason

Lack of serial log data prevented a thorough assessment of the VM's operational state. Result is
inconclusive

### Uncertain Remediation

Verify the VM's operational status by reviewing available serial logs.
Address any detected guest OS issues using the provided documentation,
keeping in mind certain guest OS faults may be beyond Google Cloud Platform's support scope.

- Viewing Serial Port Output: <https://cloud.google.com/compute/docs/troubleshooting/viewing-serial-port-output>
- Resolving Kernel Panic:
<https://cloud.google.com/compute/docs/troubleshooting/kernel-panic#resolve_the_kernel_panic_error>
- Google Cloud Platform Support Scope:
<https://cloud.google.com/compute/docs/images/support-maintenance-policy#support-scope>

### Skipped Reason

There are no logs to examine.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
