---
title: "interconnect/Bgp Down Flap"
linkTitle: "interconnect/bgp-down-flap"
weight: 3
type: docs
description: >
  This rule book analyzes BGP down and BGP flap events in a region of a project.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)
**Kind**: Debugging Tree

### Description

The following steps are executed:

  - Check BGP down status: Check if any vlan attachment has BGP down state.
  - Check Interconnect maintenance: Check if there are interconnect maintenance events
           are associated with the BGP down vlan attachments.
  - Check BGP flap status: Check if any BGP flaps happened.
  - Check Cloud Router maintenance: Check if there were Cloud Router maintenance events
           are associated with the BGP flaps.

### Executing this runbook

```shell
gcpdiag runbook interconnect/bgp-down-flap \
  -p project_id=value \
  -p region=value \
  -p start_time=value \
  -p end_time=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `region` | True | None | str | The region where the vlan attachment is located |
| `start_time` | False | None | datetime | The start window to investigate BGP flap. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time` | False | None | datetime | The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Bgp Down Flap Start](/runbook/steps/interconnect/bgp-down-flap-start)

  - [Check Bgp Down](/runbook/steps/interconnect/check-bgp-down)

  - [Check Interconnect Maintenance](/runbook/steps/interconnect/check-interconnect-maintenance)

  - [Check Bgp Flap](/runbook/steps/interconnect/check-bgp-flap)

  - [Check Cloud Router Maintenance](/runbook/steps/interconnect/check-cloud-router-maintenance)

  - [Bgp Down Flap End](/runbook/steps/interconnect/bgp-down-flap-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
