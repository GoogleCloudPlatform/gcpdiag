---
title: "gce/Disk Avg Io Latency Check"
linkTitle: "Disk Avg Io Latency Check"
weight: 3
type: docs
description: >
  Check Disk Avg IO Latency
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The performance of the disk '{disk_name}' is currently degraded due to high
IO latency exceeding optimal thresholds. This may result in slower read/write
speeds and overall reduced performance.

### Failure Remediation

Disk I/O latency is the time it takes for a read or write operation to complete on a
disk.
High disk I/O latency can significantly impact the performance of your applications
and workloads running on the instance, leading to slow response times, increased
processing time, and overall sluggishness.

**Potential Bottlenecks**
- Disk Type: To optimize disk performance, ensure your disk type is appropriate
for your workload and provides acceptable latency for your system architecture.
Choosing the right disk type can significantly impact performance.
https://cloud.google.com/compute/docs/disks

- Workload: The nature of your workload also influences latency. Workloads with
many small, random I/O operations will generally have higher latency than those
with sequential I/O

**Optimize Disk Usage**
- Reduce I/O Operations: Optimize your applications and database queries to minimize
the number of disk I/O operations.
- Increase I/O Request Size: Larger I/O requests can be more efficient than many small
ones. Consider adjusting your application or database settings to increase the I/O
request size.
- Caching: Implement caching mechanisms to reduce the need to access the disk for
frequently used data.

Choose the Right Disk Type with lesser IO Latency - https://cloud.google.com/compute/docs/disks

You may also look into Optimizing persistent disk performance -
https://cloud.google.com/compute/docs/disks/optimizing-pd-performance

Please don't hesitate to reach out to Google Cloud Support if issue is not resolved.

### Success Reason

Instance disk "{disk_name}"'s IO latency is within the optimal limits.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
