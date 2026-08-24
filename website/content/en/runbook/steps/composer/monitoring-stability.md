---
title: "composer/Monitoring Stability"
linkTitle: "Monitoring Stability"
weight: 3
type: docs
description: >
  Check the stability of the Composer environment's Monitoring Pod via cloud logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step queries Cloud Logging to see if the monitoring pod has any OOM
  events.

### Failure Reason

Monitoring Pod has restarted due to OOM.

### Failure Remediation

Upgrade to the latest composer version. For more details, refer to [documentation](https://docs.cloud.google.com/composer/docs/release-notes#February_05_2024).

### Success Reason

Monitoring Pod is running in cluster.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
