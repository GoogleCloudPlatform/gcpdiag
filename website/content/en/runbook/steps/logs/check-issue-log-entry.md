---
title: "logs/Check Issue Log Entry"
linkTitle: "Check Issue Log Entry"
weight: 3
type: docs
description: >
  Checks logs for problematic entry using filter string provided.
---

**Product**: \
**Step Type**: AUTOMATED STEP

### Description

Attributes:
    project_id(str): Project ID to search for filter
    filter_str(str): Filter written in log querying language:
      https://cloud.google.com/logging/docs/view/query-library.
      This field required because an empty filter matches all log entries.
    template(str): Custom template for logging issues related to a resource
      type
    resource_name (Optional[str]): Resource identifier that will be used in
      the custom template provided.

### Failure Reason

Problematic log entries found matching query:
{query}

### Failure Remediation

Run the following Cloud Logging query in the Google Cloud console to find the log entry indicating the problem:

Query:
{query}

### Uncertain Reason

No problematic log entries found in the time range matching the following query:

{query}

### Uncertain Remediation

1. Verify of the time range used in the filter matches that when the issue occurred and adjust it accordingly.
Query:
{query}
2. Verify that logging for the resource has not been disabled due to cost management: <https://cloud.google.com/blog/products/devops-sre/cloud-logging-cost-management-best-practices>

### Skipped Reason

Could not fetch log entries for the following due to {api_err}.

Query:
{query}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
