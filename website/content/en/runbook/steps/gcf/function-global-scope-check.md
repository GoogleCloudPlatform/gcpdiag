---
title: "gcf/Function Global Scope Check"
linkTitle: "Function Global Scope Check"
weight: 3
type: docs
description: >
  Check for deployment failures due to global scope code errors
---

**Product**: [Cloud Functions](https://cloud.google.com/functions)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

A problem with the function code was detected. The deployment pipeline completed the function deployment,
but failed at the last step- sending a health check to the function. This health check executes the function's global scope,
which may be throwing an exception, crashing, or timing out.

### Failure Remediation

Refer to the following document to address this error:
<https://cloud.google.com/functions/docs/troubleshooting#global>

### Success Reason

No issues found with function global scope.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
