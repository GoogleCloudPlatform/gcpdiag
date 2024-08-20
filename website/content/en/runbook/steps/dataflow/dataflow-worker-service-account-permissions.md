---
title: "dataflow/Dataflow Worker Service Account Permissions"
linkTitle: "Dataflow Worker Service Account Permissions"
weight: 3
type: docs
description: >
  Check the Dataflow Worker account permissions.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)\
**Step Type**: GATEWAY

### Description

Worker instances use the worker service account to access input and output
  resources after you submit your job.
  For the worker service account to be able to run a job,
  it must have the roles/dataflow.worker role.

### Failure Reason

Service Account {service_account} associated with Dataflow Job was not found in project {project_id} or cross project (if specified).

### Failure Remediation

Provide the project in which the service account resides by using the cross_project/project parameter.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
