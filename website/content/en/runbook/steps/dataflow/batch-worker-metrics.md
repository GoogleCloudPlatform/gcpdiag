---
title: "dataflow/Batch Worker Metrics"
linkTitle: "Batch Worker Metrics"
weight: 3
type: docs
description: >
  Has step to check job's workers.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)\
**Step Type**: AUTOMATED STEP

### Description

Queries the worker vcpu Promql metrics for a running job.

### Failure Reason

  High resource utilization for CPU and Memory, which may choke throughput

### Failure Remediation

  Check on CPU and memory utilization [1], if high it may indicate underprovisioning of the pipeline,
  in which case tailor the VM shape to accommodate the pipeline needs e.g. high mem or high cpu workers.
  If both resources are low but throughput is lower than expected,
   - consider profiling the pipeline to identify slow stages [2] e.g. external API,
   - check on wall time to identify stages with long processing time[3],
   - and troubleshoot stage parallelism by monitoring keys [4] e.g. high fanout and hot key stages that may need key redistribution.

  [1] <https://docs.cloud.google.com/dataflow/docs/guides/using-monitoring-intf#resource-metrics>
  [2] <https://docs.cloud.google.com/dataflow/docs/guides/profiling-a-pipeline>
  [3] <https://docs.cloud.google.com/dataflow/docs/guides/step-info-panel#wall-time>
  [4] <https://docs.cloud.google.com/dataflow/docs/guides/troubleshoot-slow-batch-jobs>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
