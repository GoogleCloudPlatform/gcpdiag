---
title: "gce/Vm Scope"
linkTitle: "Vm Scope"
weight: 3
type: docs
description: >
  Verifies that a GCE VM has at least one of a list of required access scopes
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

Confirms that the VM has the necessary OAuth scope
  https://cloud.google.com/compute/docs/access/service-accounts#accesscopesiam

  Attributes
   - Use `access_scopes` to specify eligible access scopes
   - Set `require_all` to True if the VM should have all the required access. False (default)
     means to check if it has at least one of the required access scopes

### Failure Reason

GCE VM {vm_name} doesn't have any of the required access scopes:
{required_access_scope}

### Failure Remediation

Access scopes are the legacy method of specifying authorization for your VM instance.
They define the default OAuth scopes used in requests from the gcloud CLI or the client libraries.
Access scopes don't apply for calls made using gRPC.

Update `{vm_full_path}` to enable at least one of the following access scopes:
{required_access_scope}
[1] https://cloud.google.com/compute/docs/instances/change-service-account#changeserviceaccountandscopes

### Success Reason

GCE instance {vm_name} has at least one of the required scope:
{present_access_scopes}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
