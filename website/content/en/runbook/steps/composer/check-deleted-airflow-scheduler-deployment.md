---
title: "composer/Check Deleted Airflow Scheduler Deployment"
linkTitle: "Check Deleted Airflow Scheduler Deployment"
weight: 3
type: docs
description: >
  Check the deleted airflow-scheduler deployment via Cloud Logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the deleted airflow-scheduler deployment via Cloud Logging.

### Failure Reason

Deleted airflow-scheduler deployment found in Cluster Logs.

### Failure Remediation

Create a new Managed Airflow environment and move DAGs to the new environment or contact Google Cloud Support.

### Success Reason

No deleted airflow-scheduler deployment found in Cluster Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
