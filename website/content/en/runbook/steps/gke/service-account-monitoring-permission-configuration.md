---
title: "gke/Service Account Monitoring Permission Configuration"
linkTitle: "Service Account Monitoring Permission Configuration"
weight: 3
type: docs
description: >
  Verifies that service accounts in GKE node pools have monitoring permissions.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Checks that the service accounts used by nodes in the GKE cluster
  have the essential "roles/monitoring.metricWriter" IAM permission. This
  permission is required to send metric data to Google Cloud Monitoring.

### Failure Reason

The monitoring health check failed because the service account lacks necessary permissions to write metrics.

### Failure Remediation

Grant the service account the 'roles/monitoring.metricWriter' role or equivalent permissions. See instructions:
<https://cloud.google.com/kubernetes-engine/docs/troubleshooting/dashboards#write_permissions>

### Success Reason

The service account has necessary permissions to write metrics.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
