---
title: "gke/Service Account Permission"
linkTitle: "Service Account Permission"
weight: 3
type: docs
description: >
  Step to verify that service accounts in GKE node pools have the required IAM roles.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Attributes:
      required_roles (list): list of IAM roles to check on each node-pool service account.
      template (str): the runbook template path for this check.
      service_name (str) the service for which service account permissions need to be check.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
