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

Connections from node to Google APIs timed out, preventing image pulls. This may be caused by a firewall rule blocking egress traffic to Google APIs. The specific blocked IP range might be indicated in the log entry.
Example log entry:

{log_entry}

### Failure Remediation

Ensure firewall rules permit egress traffic to Google APIs. Refer to the documentation:
<https://cloud.google.com/kubernetes-engine/docs/concepts/firewall-rules>

### Success Reason

No "Failed to pull image.*dial tcp.*i/o timeout" errors were found for cluster between {start_time} and {end_time}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
