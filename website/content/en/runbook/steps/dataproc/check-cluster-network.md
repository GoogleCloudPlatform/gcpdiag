---
title: "dataproc/Check Cluster Network"
linkTitle: "Check Cluster Network"
weight: 3
type: docs
description: >
  Verify that the nodes in the cluster can communicate with each other.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

The Compute Engine Virtual Machine instances (VMs) in a Dataproc cluster must
  be able to communicate with each other using ICMP, TCP (all ports), and UDP
  (all ports) protocols.

### Failure Reason

The network communication among nodes in cluster {cluster_name} is blocked.

### Failure Remediation

Create a firewall rule that meets Dataproc connectivity requirements[1] and apply it to the cluster's VPC network.
Review the documentation[2] for more details.
References:
[1] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/network#dataproc_connectivity_requirements>
[2] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/network>

### Success Reason

The network communication among nodes in cluster {cluster_name} is working.

### Uncertain Reason

The cluster has not been found, it may have been deleted. Skipping the connectivity test.

### Uncertain Remediation

Verify that Dataproc connectivity requirements[1] are satisfied.
References:
[1] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/network#dataproc_connectivity_requirements>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
