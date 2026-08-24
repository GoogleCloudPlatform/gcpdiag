---
title: "composer/Check Liveness Probes"
linkTitle: "Check Liveness Probes"
weight: 3
type: docs
description: >
  Checks for failed Liveness probes on worker pods.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This check verifies if there are any Liveness probes failed on worker pods.

### Failure Reason

Liveness Probes found in airflow-worker Logs.

### Failure Remediation

Follow documentation : <https://docs.cloud.google.com/composer/docs/composer-2/troubleshooting-dags#airflow-worker-load> OR Please contact Google Cloud Support.

### Success Reason

No Liveness Probes issue found in airflow-worker Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
