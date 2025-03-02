---
title: "dataproc/Check Private Google Access"
linkTitle: "Check Private Google Access"
weight: 3
type: docs
description: >
  Check if the subnetwork of the cluster has private google access enabled.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

Checking if the subnetwork of the cluster has private google access enabled.

### Failure Reason

Google Private Access in subnet: {subnetwork_uri} is disabled.

### Failure Remediation

You may create a Dataproc cluster that is isolated from the public internet whose VM instances communicate over a private IP subnetwork [cluster VMs are not assigned public IP addresses](1).
To do this, the subnetwork must have Private Google Access enabled to allow cluster nodes to access Google APIs and services, such as Cloud Storage, from internal IPs.
Please configure Private Google Access in the cluster subnet[2].
References:
[1] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/network#create-a-dataproc-cluster-with-internal-IP-addresses-only>
[2] <https://cloud.google.com/vpc/docs/configure-private-google-access>

### Success Reason

Google Private Access in subnet: {subnetwork_uri} is enabled.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
