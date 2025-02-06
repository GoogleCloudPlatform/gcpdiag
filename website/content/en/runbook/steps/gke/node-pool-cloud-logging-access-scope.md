---
title: "gke/Node Pool Cloud Logging Access Scope"
linkTitle: "Node Pool Cloud Logging Access Scope"
weight: 3
type: docs
description: >
  Verifies that GKE node pools have the required Cloud Logging access scopes.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Confirms that the nodes within the GKE cluster's node pools have the necessary
  scopes to write log data to Cloud Logging.  These scopes include
  'https://www.googleapis.com/auth/logging.write' and  potentially others,
  such as 'https://www.googleapis.com/auth/cloud-platform' and
  'https://www.googleapis.com/auth/logging.admin', depending on the configuration.

### Failure Reason

The logging health check failed because node pools have insufficient access scope for Cloud Logging.

### Failure Remediation

Adjust node pool access scope to grant necessary logging permissions. See instructions:
https://cloud.google.com/kubernetes-engine/docs/troubleshooting/logging#verify_nodes_in_the_node_pools_have_access_scope

### Success Reason

Node pools have sufficient access scope for Cloud Logging.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
