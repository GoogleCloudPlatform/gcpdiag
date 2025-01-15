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

The connection from Node to restricted.googleapis.com (199.36.153.4/30) or private.googleapis.com (199.36.153.8/30) is timing out, preventing image pull. It is probable that a firewall rule is blocking this IP range. A firewall to permit this egress should be created.
Example log entry that would help identify involved objects:

{LOG_ENTRY}

### Failure Remediation

Follow the documentation:
https://cloud.google.com/vpc-service-controls/docs/set-up-private-connectivity

### Success Reason

No "Failed to pull image.*dial tcp.*199.36.153.\d:443: i/o timeout" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
