---
title: "gke/Ca Instance Timeout"
linkTitle: "Ca Instance Timeout"
weight: 3
type: docs
description: >
  Check for "scale.up.error.waiting.for.instances.timeout" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleUp event failed because instances in some of the MIGs failed to appear in time.
Example log entry that would help identify involved objects:
{LOG_ENTRY}

### Failure Remediation

This message is transient. If it persists, engage Google Cloud Support for further investigation.

### Success Reason

No "scale.up.error.waiting.for.instances.timeout" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
