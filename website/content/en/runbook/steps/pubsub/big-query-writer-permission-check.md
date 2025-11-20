---
title: "pubsub/Big Query Writer Permission Check"
linkTitle: "Big Query Writer Permission Check"
weight: 3
type: docs
description: >
  Check that the Pub/Sub service agent has writer permissions on the table.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The Pub/Sub service account '{service_account}' does not have required BigQuery permissionson project '{project_id}'
### Failure Remediation

Grant the "BigQuery Data Editor" role (roles/bigquery.dataEditor) to the Pub/Sub service account:
'{service_account}'


<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
