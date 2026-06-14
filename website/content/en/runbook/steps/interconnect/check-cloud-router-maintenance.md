---
title: "interconnect/Check Cloud Router Maintenance"
linkTitle: "Check Cloud Router Maintenance"
weight: 3
type: docs
description: >
  Check if any Cloud Router had maintenance event.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: AUTOMATED STEP

### Description

Check if any Cloud Router had maintenance event.
  Report BGP flaps without Cloud Router maintenance event.

### Failure Reason

    Error BGP : crId:{router_id}, ip:{local_ip}, peerIp:{remote_ip}, crName:{router_name}, vlan:{attachment}, proj:{project_id}, details:{flap_details}

### Failure Remediation

    BGP flaps lasting less than {timer} seconds have been observed without Cloud Router maintenance. Analyze Cloud Router logs to identify the root cause. Check the public documentation for guidance.Logging query example <https://cloud.google.com/network-connectivity/docs/router/support/troubleshoot-log-messages> or contact GCP support.{example_query}

### Success Reason

    BGP flaps less than {timer} seconds are all caused by Cloud Router maintenance events.

### Skipped Reason

    No BGP flaps, skip cloud router mainteance check in in region `{region}` in project `{project_id}`.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
