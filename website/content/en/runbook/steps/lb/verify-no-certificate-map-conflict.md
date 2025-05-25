---
title: "lb/Verify No Certificate Map Conflict"
linkTitle: "Verify No Certificate Map Conflict"
weight: 3
type: docs
description: >
  Checks for conflicting certificate map set on a target proxy.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The following target proxies have a conflicting certificate map:

{conflicting_target_proxies}.

If certificate map is set on a target proxy, the classic SSL certificates are ignored.

### Failure Remediation

If this configuration is unintended, detach the certificate map from the target proxies.

### Success Reason

All target proxies associated with the SSL certificate "{name}" do not have a certificate map.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
