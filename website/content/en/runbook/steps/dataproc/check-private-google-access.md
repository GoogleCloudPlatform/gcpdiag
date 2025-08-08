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

Dataproc clusters isolated from the public internet require Private Google Access enabled on their subnetwork ({subnetwork_uri}) to allow cluster nodes to access Google APIs and services (e.g., Cloud Storage) using internal IPs [cluster VMs are not assigned public IP addresses](1).
Enable Private Google Access for the subnetwork[2].
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
