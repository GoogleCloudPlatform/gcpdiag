---
title: "composer/Shared Vpc Org Policy Constraint"
linkTitle: "Shared Vpc Org Policy Constraint"
weight: 3
type: docs
description: >
  Check the shared VPC org policy constraint via Cloud Logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the shared VPC org policy constraint via Cloud Logging.

### Failure Reason

Org Policy constraint violated logs found in Cluster.

### Failure Remediation

Update Policy: Add the Managed Airflow subnet to the allow list in the
Organization Policies console.

### Success Reason

No Org Policy constraint violated logs found in Cluster.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
