---
title: "gke/Gke Ip Masq Standard"
linkTitle: "gke/gke-ip-masq-standard"
weight: 3
type: docs
description: >
  This runbook will analyze symptoms for IP Masquerading issues on GKE Cluster.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

It examines the following:

  - Are there any traffic logs to destination IP?
  - Is ip-masq-agent DaemonSet in kube-system namespace?
  - Is ip-masq-agent Configmap in kube-system namespace?
  - Is GKE node IP and Pod IP are under nonMasquerade CIDR?
  - Is Destination IP is under are under nonMasquerade CIDR?

### Executing this runbook

```shell
gcpdiag runbook gke/gke-ip-masq-standard \
  -p project_id=value \
  -p src_ip=value \
  -p dest_ip=value \
  -p pod_ip=value \
  -p name=value \
  -p location=value \
  -p node_ip=value \
  -p start_time_utc=value \
  -p end_time_utc=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `src_ip` | False | None | IPv4Address | The source IP from where connection is generated |
| `dest_ip` | True | None | IPv4Address | The Destination IP is where the request is sending (Example : 8.8.8.8) |
| `pod_ip` | False | None | str | GKE Pod IP address or pod address range(Example 192.168.1.0/24) |
| `name` | False | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `location` | False | None | str | The zone or region of the GKE cluster |
| `node_ip` | False | None | str | GKE Node IP address or address range/CIDR (Example 192.168.1.0/24) |
| `start_time_utc` | False | None | datetime | Start time of the issue |
| `end_time_utc` | False | None | datetime | End time of the issue |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Gke Ip Masq Standard Start](/runbook/steps/gke/gke-ip-masq-standard-start)

  - [Nodeproblem](/runbook/steps/gke/nodeproblem)

  - [Check Daemon Set](/runbook/steps/gke/check-daemon-set)

  - [Check Config Map](/runbook/steps/gke/check-config-map)

  - [Check Pod I P](/runbook/steps/gke/check-pod-i-p)

  - [Check Node I P](/runbook/steps/gke/check-node-i-p)

  - [Check Destination I P](/runbook/steps/gke/check-destination-i-p)

  - [Gke Ip Masq Standard End](/runbook/steps/gke/gke-ip-masq-standard-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
