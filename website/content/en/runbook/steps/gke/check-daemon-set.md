---
title: "gke/Check Daemon Set"
linkTitle: "Check Daemon Set"
weight: 3
type: docs
description: >
  On GKE for ip-masq can be deployed or automatically in cluster.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This step will verify if Daemon set present?

### Uncertain Reason

Check for ip-masq-agent daemonSet is deployed in the Cluster. If yes follow check next step.

### Uncertain Remediation

If No, please follow [1] to deploy ip-masq-agent DaemonSet in the kube-system namespace and wait for around 5 minutes
for the DaemonSet to be ready.

[1] <https://cloud.google.com/kubernetes-engine/docs/how-to/ip-masquerade-agent#checking_the_ip-masq-agent_daemonset>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
