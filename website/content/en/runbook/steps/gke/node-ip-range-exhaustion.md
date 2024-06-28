---
title: "gke/Node Ip Range Exhaustion"
linkTitle: "Node Ip Range Exhaustion"
weight: 3
type: docs
description: >
  Check Node IP Range Exhaustion and offer remediation.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Checks Node IP range exhaustion and offers remediation step.

### Failure Reason

  Node IP exhaustion is detected in the cluster {cluster_name}:

  {status_message}


### Failure Remediation

  Follow [1] to expand the ip range of the node subnet.

  [1] https://cloud.google.com/vpc/docs/create-modify-vpc-networks#expand-subnet

### Success Reason

  Node IP exhaustion is detected in the cluster {cluster_name}:

  {status_message}




<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
