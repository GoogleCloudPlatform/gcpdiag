---
title: "gke/Unallocatable Gpu"
linkTitle: "Unallocatable Gpu"
weight: 3
type: docs
description: >
  Checks GPU allocation
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {node} was auto-repaired because it had unallocatable GPU(s) for more than 15 minutes.

### Failure Remediation

The auto-repair should have fixed the detected unallocatable GPU(s).
For more details check: <https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-repair>

### Success Reason

The node {node} was auto-repaired for reasons other than unallocatable GPU(s).



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
