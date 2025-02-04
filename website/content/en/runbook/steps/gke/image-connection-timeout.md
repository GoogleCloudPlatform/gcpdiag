---
title: "gke/Image Connection Timeout"
linkTitle: "Image Connection Timeout"
weight: 3
type: docs
description: >
  The connection to Google APIs is timing out
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The connection from Node to Google APIs is timing out. It is probable that a firewall rule is blocking this IP range.
Expand results to see the blocked IP range.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

Follow the documentation:
https://cloud.google.com/kubernetes-engine/docs/concepts/firewall-rules

### Success Reason

No "Failed to pull image.*dial tcp.*i/o timeout" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
