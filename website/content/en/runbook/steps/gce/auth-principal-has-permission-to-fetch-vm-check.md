<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
---
title: "gce/Auth Principal Has Permission To Fetch Vm Check"
linkTitle: "Auth Principal Has Permission To Fetch Vm Check"
weight: 3
type: docs
description: >
  Validates if a user has the necessary permissions to retrieve information about a GCE instance.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step checks for specific permissions related to instance retrieval.
  It is critical for ensuring that the user executing the SSH command with gcloud or console has
  the ability to access detailed information about the instance in question.

### Failure Reason

The authenticated user {auth_user} does not have the permissions needed to manage instances.
The following permissions are required: {instance_permissions}.

### Failure Remediation

To remedy this, ensure the user {auth_user} is granted a role encompassing the necessary permissions:
- Permissions needed: {instance_permissions}
For guidance on assigning instance admin roles, consult:
https://cloud.google.com/compute/docs/access/iam#connectinginstanceadmin

### Success Reason

The user {auth_user} possesses the appropriate permissions to fetch instance details.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
