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

Found logs messages related to "{log}" on the cluster: {cluster_name}.

### Failure Remediation

This issue occurs when Spark Jobs was not able to find available port after 1000 retries.
COLSE_WAIT connections are possible cause of this issue.
To identify any CLOSE_WAIT connections, please analyze the netstat output.
1. netstat plant >> open_connections.txt
2. cat open_connections.txt | grep “CLOSE_WAIT”

If the blocked connections are due to a specific application, restarting that application is recommended.
Alternatively, restarting the master node will also release the affected connections.

### Success Reason

Didn't find logs messages related to "{log}" on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
