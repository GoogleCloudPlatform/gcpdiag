---
title: "gke/Check Config Map"
linkTitle: "Check Config Map"
weight: 3
type: docs
description: >
  This will confirm confif map is present as that llow user to make changes on ip-agent.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This will check if config map is present ?

### Uncertain Reason

When ip-masq-agent daemonset is deployed without a configmap, it uses the default non-masq destinations [1].

[1] https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#creating_the_ip-masq-agent_configmap

### Uncertain Remediation

If you needs to customize the configmap, then follow the steps [1] to deploy ip-masq-agent ConfigMap in the kube-system
namespace.
[1] https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#creating_the_ip-masq-agent_configmap



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
