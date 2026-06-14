---
title: "gke/Node Pool Cloud Monitoring Access Scope Configuration"
linkTitle: "Node Pool Cloud Monitoring Access Scope Configuration"
weight: 3
type: docs
description: >
  Verifies that GKE node pools have the required Cloud Monitoring access scopes.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Confirms that the nodes within the GKE cluster's node pools have the necessary
  scopes to write metrics data to Cloud Monitoring.  These scopes include
  'https://www.googleapis.com/auth/monitoring' and potentially others,
  such as 'https://www.googleapis.com/auth/cloud-platform' and
  'https://www.googleapis.com/auth/monitoring.write', depending on the configuration.

### Failure Reason

The monitoring health check failed because node pools have insufficient access scope for Cloud Monitoring.

### Failure Remediation

Adjust node pool access scope to grant necessary monitoring permissions. See instructions:
<https://cloud.google.com/kubernetes-engine/docs/how-to/access-scopes#default_access_scopes>

### Success Reason

Node pools have sufficient access scope for Cloud Monitoring.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
