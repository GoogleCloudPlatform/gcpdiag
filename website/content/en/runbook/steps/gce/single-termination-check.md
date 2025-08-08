---
title: "gce/Single Termination Check"
linkTitle: "Single Termination Check"
weight: 3
type: docs
description: >
  Investigates the cause of a single VM termination.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

It analyzes log entries to identify whether the termination was normal or abnormal
    and prepares a Root Cause Analysis (RCA) based on the findings.

    The investigation focuses on the first occurring termination, assuming that any subsequent
    terminations are inconsequential

### Success Reason

No GCE Instance was terminated between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
