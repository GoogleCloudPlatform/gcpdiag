<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
---
title: "gce/Windows Guest Os Checks"
linkTitle: "Windows Guest Os Checks"
weight: 3
type: docs
description: >
  Diagnoses common issues related to Windows Guest OS, focusing on boot-up processes and SSHD.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: COMPOSITE STEP

### Description

This composite diagnostic step evaluates the VM's metadata to ensure SSH is enabled for Windows,
  checks serial logs for successful boot-up patterns, and involves a manual check on the Windows SSH
  agent status. It aims to identify and help troubleshoot potential issues that could impact the
  VM's accessibility via SSHD



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
