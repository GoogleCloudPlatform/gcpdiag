---
title: "gke/Image Connection Timeout Restricted Private"
linkTitle: "Image Connection Timeout Restricted Private"
weight: 3
type: docs
description: >
  The connection to restricted.googleapis.com or private.googleapis.com is timing out
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Connections from node to restricted.googleapis.com (199.36.153.4/30) or private.googleapis.com (199.36.153.8/30) timed out, preventing image pulls. This may be caused by a firewall rule blocking egress traffic to these IP ranges.
Example log entry:

{log_entry}

### Failure Remediation

Ensure firewall rules permit egress traffic to restricted.googleapis.com (199.36.153.4/30) or private.googleapis.com (199.36.153.8/30). Refer to the documentation:
<https://cloud.google.com/vpc-service-controls/docs/set-up-private-connectivity>

### Success Reason

No "Failed to pull image.*dial tcp.*199.36.153.\d:443: i/o timeout" errors were found for cluster between {start_time} and {end_time}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
