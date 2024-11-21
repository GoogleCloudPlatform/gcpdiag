---
title: "dataproc/Check Bq Connector"
linkTitle: "Check Bq Connector"
weight: 3
type: docs
description: >
  Check for issues related to BigQuery connector such as version dependency conflicts.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Success Reason

You are using image version {image_version} that preinstalls BigQuery connector
and not providing any conflicting BigQuery jars on your end. There should be no dependency version conflict on the BigQuery side.

Visit Dataproc Version page to find out each component version preinstalled on your cluster:
https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters

### Uncertain Reason

You are using image version {image_version} that preinstalls BigQuery connector
and you are installing on the cluster or job level a different version of the BigQuery connector.
This might cause dependency version conflicts and fail your jobs.

### Uncertain Remediation

Try one of the following:
- (if you provide BQ jar on the cluster) Create Dataproc cluster without any BigQuery jar
- (if you provide BQ jar on the job) Run the job without any BigQuery jar
- (if you need to install BQ jar) Match the version of the BQ jar to the version preinstalled on the cluster.
For image version {image_version}, it is {bq_version}.

Visit Dataproc Version page to find out each component version preinstalled on your cluster:
https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
