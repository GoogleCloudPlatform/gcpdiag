---
title: "interconnect/Check Bgp Flap"
linkTitle: "Check Bgp Flap"
weight: 3
type: docs
description: >
  Check if any BGP flap events, report error flaps with duration over 60 seconds.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: AUTOMATED STEP

### Description

Check if any BGP flap events, report error flaps with duration over 60 seconds.

### Failure Reason

    Abnormal long BGP flaps:  crId:{router_id}, ip:{local_ip}, peerIp:{remote_ip}, crName:{router_name}, vlan:{attachment}, proj:{project_id}, details:{flap_details}

### Failure Remediation

    BGP flaps lasting longer than `{timer}` seconds are unlikely to be caused by Cloud Router maintenance events. Analyze Cloud Router logs to identify the root cause. Check the public documentation for guidance.<https://cloud.google.com/network-connectivity/docs/router/support/troubleshoot-log-messages> or contact GCP support.Logging query example {example_query}

### Success Reason

    No BGP flaps are found in region `{region}` in project `{project_id}`.

### Uncertain Reason

    Short duration BGP flaps: crId:{router_id}, ip:{local_ip}, peerIp:{remote_ip}, crName:{router_name}, vlan:{attachment}, proj:{project_id}, details:{flap_details}

### Uncertain Remediation

    Continue runbook to check if there are `cloud router maintenance` events align with BGP flaps.

### Skipped Reason

    Unable to fetch any vlan attachments to check BGP flap in any region in project `{project_id}`.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
