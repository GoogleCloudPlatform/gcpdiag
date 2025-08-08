---
title: "gce/Vm Has A Service Account"
linkTitle: "Vm Has A Service Account"
weight: 3
type: docs
description: >
  Verifies the existence of a service account for the Ops Agent to use.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This investigation only happens from the perspective googleapis and
  user provided input. We don't look inside the VM for cases like
  GOOGLE_APPLICATION_CREDENTIALS. User will have to know and specify that if
  They are using the application

### Failure Reason

The Ops Agent on instance {full_resource_path} is not configured with a service account for exporting logs and metrics.

### Failure Remediation

Attach an active service account to the GCE Instance {full_resource_path}.
Consult the following documentation for guidance:

- Attaching or changing a service account:
  <https://cloud.google.com/compute/docs/instances/change-service-account#changeserviceaccountandscopes>
- Authorizing the Ops Agent:
  <https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/authorization#authorize_with_an_attached_service_account>

### Success Reason

The Ops Agent on instance {full_resource_path} is configured with service account {sa} for exporting logs and metrics.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
