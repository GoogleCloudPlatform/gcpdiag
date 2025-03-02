---
title: "gke/Ca Out Of Resources"
linkTitle: "Ca Out Of Resources"
weight: 3
type: docs
description: >
  Check for "scale.up.error.out.of.resources" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleUp event failed because some of the MIGs could not be increased due to lack of resources.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

Follow the documentation:
<https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-vm-creation#resource_availability>

### Success Reason

No "scale.up.error.out.of.resources" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
