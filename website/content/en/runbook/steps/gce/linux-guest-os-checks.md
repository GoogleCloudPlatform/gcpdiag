---
title: "gce/Linux Guest Os Checks"
linkTitle: "Linux Guest Os Checks"
weight: 3
type: docs
description: >
  Examines Linux-based guest OS's serial log entries for guest os level issues.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: COMPOSITE STEP

### Description

This composite step scrutinizes the VM's serial logs for patterns indicative of kernel panics,
  problems with the SSH daemon, and blocks by SSH Guard - each of which could signify underlying
  issues affecting the VM's stability and accessibility. By identifying these specific patterns,
  the step aims to isolate common Linux OS and application issues, facilitating targeted
  troubleshooting.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
