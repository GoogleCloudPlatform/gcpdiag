---
title: "composer/Plugins Directory Check"
linkTitle: "Plugins Directory Check"
weight: 3
type: docs
description: >
  Check if the Composer environment's plugins directory exists.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step queries Cloud Logging to see if the environment has any logs
  indicating that the plugins directory is missing.

### Failure Reason

Plugins directory is missing in the bucket.

### Failure Remediation

Empty the directory instead of deleting it to remove plugins. Recreate the plugins directory if it is missing.

### Success Reason

No issues with Plugins directory.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
