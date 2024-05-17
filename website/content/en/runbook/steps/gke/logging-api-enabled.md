---
title: "gke/Logging Api Enabled"
linkTitle: "Logging Api Enabled"
weight: 3
type: docs
description: >
  Verifies if the Cloud Logging API is enabled for the project hosting the GKE cluster.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This initial step ensures that the fundamental infrastructure for
  logging within the project is operational. If the Cloud Logging API
  is disabled, logs from the GKE cluster won't be collected or stored
  by Google Cloud.

### Failure Reason

The logging health check failed because the Cloud Logging API is not enabled for the project.

### Failure Remediation

Enable the Cloud Logging API for your project through the Google Cloud Console or relevant API calls. See instructions: https://cloud.google.com/kubernetes-engine/docs/troubleshooting/logging#verify_logging_is_enabled_in_the_project

### Success Reason

The Cloud Logging API is enabled for the project.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
