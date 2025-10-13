---
title: "gce/Vm Duplicate Ssh Keys Check"
linkTitle: "Vm Duplicate Ssh Keys Check"
weight: 3
type: docs
description: >
  Check if there are duplicate ssh keys in VM metadata.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

VM {instance_name} has {count} duplicate SSH key(s) in its metadata: {keys}

### Failure Remediation

Remove duplicate SSH keys from the instance or project metadata to avoid potential SSH issues and improve security hygiene.

### Success Reason

No duplicate SSH keys were found in metadata for VM {instance_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
