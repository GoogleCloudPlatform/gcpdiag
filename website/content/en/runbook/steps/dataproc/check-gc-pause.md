---
title: "dataproc/Check Gc Pause"
linkTitle: "Check Gc Pause"
weight: 3
type: docs
description: >
  Verify if STW GC Pause has happened.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Failure Reason

Log messages related to "{log}" were found on the cluster: {cluster_name}.

### Failure Remediation

To address potential GC pause issues:

- Increase the `spark.executor.memory` configuration to allocate additional memory if allocated memory appears insufficient [1].
- If memory allocation seems adequate, investigate potential garbage collection optimization. Refer to the Apache Spark documentation for a comprehensive guide on Garbage Collection Tuning [2].
- Additionally, tuning the `spark.memory.fraction` property can be effective, particularly for workloads that rely heavily on RDD caching. Refer to the Memory Management Overview [3] for a detailed discussion of this configuration property.

[1] <https://spark.apache.org/docs/latest/configuration.html>
[2] <https://spark.apache.org/docs/latest/tuning.html#garbage-collection-tuning>
[3] <https://spark.apache.org/docs/latest/tuning.html#memory-management-overview>

### Success Reason

No log messages related to "{log}" were found on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
