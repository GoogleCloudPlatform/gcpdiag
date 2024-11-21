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

Found logs messages related to "{log}" on the cluster: {cluster_name}.

### Failure Remediation

If allocated memory appears insufficient, consider increasing the spark.executor.memory configuration to allocate additional memory.[1]
If memory allocation seems adequate, investigate potential garbage collection optimization. The Apache Spark documentation provides a comprehensive guide on Garbage Collection Tuning.[2]
Additionally, there is some guidance that tuning spark.memory.fraction can be effective, particularly for workloads that heavily rely on RDD caching. See Memory Management Overview for more discussion of this configuration property.
Additionally, tuning the spark.memory.fraction can be effective, particularly for workloads that rely heavily on RDD caching. Refer to the Memory Management Overview for a detailed discussion of this configuration property.

[1] https://spark.apache.org/docs/latest/configuration.html
[2] https://spark.apache.org/docs/latest/tuning.html#garbage-collection-tuning
[3] https://spark.apache.org/docs/latest/tuning.html#memory-management-overview

### Success Reason

Didn't find logs messages related to "{log}" on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
