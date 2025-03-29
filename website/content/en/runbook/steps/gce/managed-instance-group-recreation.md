---
title: "gce/Managed Instance Group Recreation"
linkTitle: "Managed Instance Group Recreation"
weight: 3
type: docs
description: >
  Investigate if an instance recreation by MIG was normal
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

Determines if the instance was recreated as part of a normal Managed Instance Group (MIG) process.

### Failure Reason

{status_message}

### Failure Remediation

Instance "{full_resource_path}" was terminated as part of a normal Managed Instance Group recreation process
and a replacement instance has been created after this termination. No action required.
[1] <https://cloud.google.com/compute/docs/instance-groups/working-with-managed-instances#autoscaling>
[2] <https://cloud.google.com/compute/docs/autoscaler>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
