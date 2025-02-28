---
title: "gke/Check Pod Ip"
linkTitle: "Check Pod Ip"
weight: 3
type: docs
description: >
  GKE preserves the Pod IP addresses sent to destinations in the nonMasqueradeCIDRs list.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This will confirm if pod IP is present on the list.

### Uncertain Reason

When ip-masq-agent daemonset is deployed without a configmap, it uses the default non-masq destinations [1].

[1] <https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#creating_the_ip-masq-agent_configmap>

### Uncertain Remediation

Follow the steps for including the pod IP CIDRs in nonMasqueradeCIDRs [1].

[1] <https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#edit-ip-masq-agent-configmap>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
