---
title: "vertex/Check Workbench Instance External Ip Disabled"
linkTitle: "Check Workbench Instance External Ip Disabled"
weight: 3
type: docs
description: >
  Check if the Workbench Instance has external IP disabled
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

If the instance has external IP disabled, user must configure
  Private networking correctly

### Success Reason

OK! Workbench Instance {instance_name} has an external IP

### Uncertain Reason

Workbench Instance {instance_name} has external IP disabled.

- network: {network}
- subnetwork: {subnetwork}
This may cause networking issues if configuration was not done correctly.

### Uncertain Remediation

Follow the public documentation to configure Private Networking for a Workbench Instance [1] [2] [3] [4]

[1] <https://cloud.google.com/vertex-ai/docs/workbench/instances/create#network-options>
[2] <https://cloud.google.com/vpc/docs/access-apis-external-ip#requirements>
[3] <https://cloud.google.com/vpc/docs/configure-private-google-access>
[4] <https://cloud.google.com/vpc/docs/configure-private-google-access#requirements>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
