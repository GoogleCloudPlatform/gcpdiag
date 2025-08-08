---
title: "gke/Node Disk Full"
linkTitle: "Node Disk Full"
weight: 3
type: docs
description: >
  Checks if node disks are full.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {node} was auto-repaired because it had disk pressure for more than 30 minutes.

### Failure Remediation

The auto-repair should have fixed the detected disk pressure.
For more details check: <https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-repair>

### Success Reason

The node {node} was auto-repaired for reasons other than disk pressure.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
