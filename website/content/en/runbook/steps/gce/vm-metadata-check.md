---
title: "gce/Vm Metadata Check"
linkTitle: "Vm Metadata Check"
weight: 3
type: docs
description: >
  Validates a specific boolean metadata key-value pair on a GCE Instance instance.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the VM's metadata contains a specified key with the expected boolean value,
  facilitating configuration verification and compliance checks.

### Failure Reason

GCE Instance metadata `{metadata_key}` doesn't have the expected value: {expected_value}
of type {expected_value_type}

### Failure Remediation

Update the metadata `{metadata_key}` to have the expected value {expected_value}
Follow guide [1] one to update the a metadata value.
[1] <https://cloud.google.com/compute/docs/metadata/setting-custom-metadata#gcloud>

### Success Reason

GCE Instance metadata `{metadata_key}` has the expected value: {expected_value}
of type {expected_value_type}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
