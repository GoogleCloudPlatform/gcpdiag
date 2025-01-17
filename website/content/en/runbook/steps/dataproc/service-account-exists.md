---
title: "dataproc/Service Account Exists"
linkTitle: "Service Account Exists"
weight: 3
type: docs
description: >
  Verify service account and permissions in Dataproc cluster project or another project.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: GATEWAY

### Description

Decides whether to check for service account roles
  - in CROSS_PROJECT_ID, if specified by customer
  - in PROJECT_ID

### Failure Reason

Service Account {service_account} associated with Dataproc cluster was not found in project {project_id} or cross project (if specified).

### Failure Remediation

Provide
project in which the service account resides by using the cross_project parameter.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
