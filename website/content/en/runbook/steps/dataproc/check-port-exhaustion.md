---
title: "dataproc/Check Port Exhaustion"
linkTitle: "Check Port Exhaustion"
weight: 3
type: docs
description: >
  Verify if the port exhaustion has happened.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Failure Reason

Log messages related to "{log}" were found on the cluster: {cluster_name}.

### Failure Remediation

This issue occurs when Spark jobs cannot find an available port after 1000 retries.
CLOSE_WAIT connections are a possible cause.
To identify CLOSE_WAIT connections, analyze the netstat output:

1. Run `netstat -plant >> open_connections.txt`.
2. Run `cat open_connections.txt | grep "CLOSE_WAIT"`.

If blocked connections are due to a specific application, restart that application.
Alternatively, restart the master node to release the affected connections.

### Success Reason

No log messages related to "{log}" were found on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
