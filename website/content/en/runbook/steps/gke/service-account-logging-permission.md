---
title: "gke/Service Account Logging Permission"
linkTitle: "Service Account Logging Permission"
weight: 3
type: docs
description: >
  Verifies the service accounts associated with node pools have 'logging.logWriter' permissions.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Checks that the service accounts used by nodes in the GKE cluster
  have the essential "roles/logging.logWriter" IAM permission. This
  permission is required to send log data to Google Cloud Logging.

### Failure Reason

The logging health check failed because the service account lacks necessary permissions to write logs.

### Failure Remediation

Grant the service account the 'roles/logging.logWriter' role or equivalent permissions. See instructions: https://cloud.google.com/kubernetes-engine/docs/troubleshooting/logging#verify_the_node_pools_service_account_has_a_role_with_the_correct_permissions

### Success Reason

The service account has necessary permissions to write logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
