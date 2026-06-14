---
title: "gke/Cluster Level Monitoring Configuration Enabled"
linkTitle: "Cluster Level Monitoring Configuration Enabled"
weight: 3
type: docs
description: >
  Verifies that monitoring is enabled at the GKE cluster level.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Confirms that the GKE cluster configuration explicitly enables
  monitoring. Even if the project has the Cloud Monitoring API enabled
  and other settings are correct, monitoring won't be collected if
  cluster-level monitoring is disabled .

### Failure Reason

The monitoring health check failed because cluster-level monitoring is not enabled.

### Failure Remediation

Enable cluster-level monitoring for the Kubernetes cluster. This can be done through the Google Cloud Console or
GKE-specific tools. See instructions:
<https://cloud.google.com/kubernetes-engine/docs/concepts/observability>

### Success Reason

Cluster-level monitoring is enabled for the cluster.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
