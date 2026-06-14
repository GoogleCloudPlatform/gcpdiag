---
title: "gke/Monitoring Api Configuration Enabled"
linkTitle: "Monitoring Api Configuration Enabled"
weight: 3
type: docs
description: >
  Verifies if the Cloud Monitoring API is enabled for the project.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This initial step ensures that the fundamental infrastructure for
  monitoring within the project is operational. If the Cloud Monitoring API
  is disabled, monitoring from the GKE cluster won't be collected or stored
  by Google Cloud.

### Failure Reason

The Monitoring health check failed because the Cloud Monitoring API is not enabled for the project.

### Failure Remediation

Enable the Cloud Monitoring API for the project through the Google Cloud Console or relevant API calls. See instructions:
<https://cloud.google.com/monitoring/api/enable-api#enabling-api-v3>

### Success Reason

The Cloud Monitoring API is enabled for the project.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
