---
title: "gce/Auth Principal Has Iap Tunnel User Permissions Check"
linkTitle: "Auth Principal Has Iap Tunnel User Permissions Check"
weight: 3
type: docs
description: >
  Verifies if the authenticated user has the required IAP roles to establish a tunnel to a VM.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step examines scenarios where users need to tunnel into a VM via IAP. It checks if the
  user has the 'roles/iap.tunnelResourceAccessor' role at the project level, necessary for
  initiating an Identity-Aware Proxy tunnel. The check focuses on project-level roles, not
  considering more granular permissions that might be assigned directly to the VM or inherited
  from higher-level resources.

### Failure Reason

"{auth_user}" lacks the "{iap_role}" role necessary to Tunnel through IAP for access.

### Failure Remediation

Ensure "{auth_user}" is granted the "{iap_role}" role. Resource guide:
https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#configure_users
https://cloud.google.com/iam/docs/manage-access-service-accounts#grant-single-role

### Success Reason

"{auth_user}" has the requisite "{iap_role}" role to tunell through IAP.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
