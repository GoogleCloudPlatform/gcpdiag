---
title: "gke/Logs Start"
linkTitle: "Logs Start"
weight: 3
type: docs
description: >
  Initiates diagnostics for GKE Clusters.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: START

### Description

- **Initial Checks:**
    - Verifies if logging API is enabled for the project.
    - Validates that there are GKE clusters in the project.
    - (Optional) If a cluster name is provided, checks if that cluster exists in the project.
    - (Optional) If a location is provided, verifies there are clusters in that location.
    - (Optional) If both a location and a name are provided, verifies that the cluster
    exists at that location.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
