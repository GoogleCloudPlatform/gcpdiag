---
title: "composer/Snapshot Load Stability"
linkTitle: "Snapshot Load Stability"
weight: 3
type: docs
description: >
  Check the stability of the Composer environment's Snapshot Load via cloud logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step queries Cloud Logging to see if the snapshot load had any issues.

### Failure Reason

Snapshot load has failed.

### Failure Remediation

To mitigate the issue, remove unnecessary connections or variables and load the snapshot again. If the issue persists, contact Google Cloud Support for assistance.

### Success Reason

No issues with snapshot load.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
