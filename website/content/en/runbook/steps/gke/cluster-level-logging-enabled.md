---
title: "gke/Cluster Level Logging Enabled"
linkTitle: "Cluster Level Logging Enabled"
weight: 3
type: docs
description: >
  Verifies that logging is enabled at the GKE cluster level.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Confirms that the GKE cluster configuration explicitly enables
  logging. Even if the project has the Cloud Logging API enabled
  and other settings are correct, logs won't be collected if
  cluster-level logging is disabled.

### Failure Reason

The logging health check failed because cluster-level logging is not enabled.

### Failure Remediation

Enable cluster-level logging for your Kubernetes cluster. This can be done through the Google Cloud Console or GKE-specific tools. See instructions: https://cloud.google.com/kubernetes-engine/docs/troubleshooting/logging#verify_logging_is_enabled_on_the_cluster

### Success Reason

Cluster-level logging is enabled for the cluster.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
