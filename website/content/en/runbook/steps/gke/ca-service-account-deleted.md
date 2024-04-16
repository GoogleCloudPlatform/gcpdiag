---
title: "gke/Ca Service Account Deleted"
linkTitle: "Ca Service Account Deleted"
weight: 3
type: docs
description: >
  Check for "scale.up.error.service.account.deleted" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleUp event failed because a service account used by Cluster Autoscaler has been deleted.
Example log entry that would help identify involved objects:
{LOG_ENTRY}

### Failure Remediation

Engage Google Cloud Support for further investigation.

### Success Reason

No "scale.up.error.service.account.deleted" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
