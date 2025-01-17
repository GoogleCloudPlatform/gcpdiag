---
title: "gce/Posix User Has Valid Ssh Key Check"
linkTitle: "Posix User Has Valid Ssh Key Check"
weight: 3
type: docs
description: >
  Verifies the existence of a valid SSH key for the specified local Proxy user on a (VM).
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

Ensures that the local user has at least one valid SSH key configured in the VM's metadata, which
  is essential for secure SSH access. The check is performed against the SSH keys stored within
  the VM's metadata. A successful verification indicates that the user is likely able to SSH into
  the VM using their key.

### Failure Reason

The local user "{local_user}" lacks at least one valid SSH key for VM: "{vm_name}".

### Failure Remediation

Ensure "{local_user}" has a valid SSH key by following the guide:
https://cloud.google.com/compute/docs/connect/add-ssh-keys#add_ssh_keys_to_instance_metadata

### Success Reason

The local user "{local_user}" is confirmed to have at least one valid SSH key
configured on the GCE VM: "{vm_name}".



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
