---
title: "gce/Vm Has A Service Account"
linkTitle: "Vm Has A Service Account"
weight: 3
type: docs
description: >
  Verifies the existance of a service account for the Ops Agent to use.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This investigation only happens from the perspective googleapis and
  user provided input. We don't look inside the VM for cases like
  GOOGLE_APPLICATION_CREDENTIALS. User will have to know and specify that if
  They are using the application

### Failure Reason

Ops agent in {vm_name} doesn't have a service account to use when
exporting logs/metrics.

### Failure Remediation

Follow [1] to attach an active service account to this GCE VM.
Read more on how to properly authorize ops agent.
[1] https://cloud.google.com/compute/docs/instances/change-service-account#changeserviceaccountandscopes
[2] https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/authorization#authorize_with_an_attached_service_account

### Success Reason

Ops agent in {vm_name} has {sa} to use when exporting logs/metrics



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
