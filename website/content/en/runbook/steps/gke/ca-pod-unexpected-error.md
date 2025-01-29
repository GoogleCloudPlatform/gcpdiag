---
title: "gke/Ca Pod Unexpected Error"
linkTitle: "Ca Pod Unexpected Error"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.pod.unexpected.error" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Pod is blocking the ScaleDown event because of an unexpected error.
Example log entry that would help identify involved objects:
{LOG_ENTRY}

### Failure Remediation

The root cause of this error is unknown. Contact Cloud Customer Care for further investigation.

### Success Reason

No "no.scale.down.node.pod.unexpected.error" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
