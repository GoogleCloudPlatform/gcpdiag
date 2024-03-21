---
title: "gce/Auth Principal Has Compute Metadata Permissions Check"
linkTitle: "Auth Principal Has Compute Metadata Permissions Check"
weight: 3
type: docs
description: >
  Verifies if the authenticated user has permissions to update SSH metadata.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the user has the necessary permissions to modify SSH metadata at
  the project or instance level. It focuses on project-level permissions and does not consider
  permissions inherited from ancestor resources like folders or organizations.

### Failure Reason

The current user does not have the necessary permissions to modify metadata,
essential for managing SSH keys. Missing permissions include one of the following:
.

### Failure Remediation

To grant the required permissions for managing SSH keys within the VM's metadata, follow these guides:
- For project-level SSH key management, assign roles that include the
'compute.projects.setCommonInstanceMetadata' permission. More details can be found here:
https://cloud.google.com/compute/docs/connect/add-ssh-keys#expandable-2
- For instance-level SSH key management, ensure roles include 'compute.instances.setMetadata'
permission. Step-by-step instructions are available here:
https://cloud.google.com/compute/docs/connect/add-ssh-keys#expandable-3
Adjusting these permissions will allow for the proper management of SSH keys and, by extension,
SSH access to the VM especially if using gcloud / cloud console.

### Success Reason

{auth_user} is authorized to update instance or project metadata, including SSH keys.
This enables gcloud and cloud console to update temporary SSH access to the VM or configure
personal SSH keys if needed.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
