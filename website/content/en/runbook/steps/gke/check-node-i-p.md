---
title: "gke/Check Node I P"
linkTitle: "Check Node I P"
weight: 3
type: docs
description: >
  When Node IP is present under non-masquerade list, it will allow node IP to not get natted .
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This will check node IP address is present default non-masquerade destinations.

### Uncertain Reason

When ip-masq-agent daemonset is deployed without a configmap, it uses the default non-masq destinations [1].

[1] https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#creating_the_ip-masq-agent_configmap

### Uncertain Remediation

Follow the steps for including the Node IP CIDRs in nonMasqueradeCIDRs [1].

[1] https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#edit-ip-masq-agent-configmap



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
