---
title: "gce/Gce Log Check"
linkTitle: "Gce Log Check"
weight: 3
type: docs
description: >
  Executes a Cloud Logging query and checks results against optional patterns.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step queries Cloud Logging using the provided filter string by calling
  logs.generalized_steps.CheckIssueLogEntry.
  See CheckIssueLogEntry for logic on FAILED/UNCERTAIN status.

  Parameters retrieved via `op.get()`:
    project_id(str): Project ID to search for filter.
    filter_str(str): Filter in Cloud Logging query language:
      https://cloud.google.com/logging/docs/view/query-library.
    issue_pattern(Optional[str]): Semicolon-separated ';;' list of regex
      patterns to search for in `protoPayload.status.message`. If prefixed
      with 'ref:', it resolves to a list in `gce/constants.py`.
      If provided, logs matching pattern will result in FAILED status.
    resource_name(Optional[str]): Resource identifier for template messages.
    template(Optional[str]): Template name, defaults to
      'logging::gce_log'.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
