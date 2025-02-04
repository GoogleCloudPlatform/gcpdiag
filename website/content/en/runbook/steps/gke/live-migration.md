---
title: "gke/Live Migration"
linkTitle: "Live Migration"
weight: 3
type: docs
description: >
  Checks if the node was unavailable due to a live migration event.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Live migration check failed for node {node}.

### Failure Remediation

There was a live migration event for the node {node}.

For more details about Live migration process during maintenance events, please consult the documentation:
https://cloud.google.com/compute/docs/instances/live-migration-process

### Success Reason

The node {node} was unavailable for reasons other than live migration.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
