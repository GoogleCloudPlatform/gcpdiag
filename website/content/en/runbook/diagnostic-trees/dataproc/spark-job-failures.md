---
title: "dataproc/Spark Job Failures"
linkTitle: "dataproc/spark-job-failures"
weight: 3
type: docs
description: >
  Provides a comprehensive analysis of common issues which affects Dataproc Spark job failures.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)
**Kind**: Debugging Tree

### Description

This runbook focuses on a range of potential problems for Dataproc Spark jobs
  on
  Google Cloud Platform. By conducting a series of checks, the runbook aims to
  pinpoint the root cause of Spark job failures.

  The following areas are examined:

  - Cluster version supportability: Evaluates if the job was run on a supported
  cluster image version.
  - Permissions: Checks for permission related issues on the cluster and GCS
  bucket level.
  - OOM: Checks Out-Of-Memory issues for the Spark job on master or worker
  nodes.
  - Logs: Check other logs related to shuffle failures, broken pipe, YARN
  runtime exception, import failures.
  - Throttling: Checks if the job was throttled and provides the exact reason
  for it.
  - GCS Connector: Evaluates possible issues with the GCS Connector.
  - BigQuery Connector: Evaluates possible issues with BigQuery Connector, such
  as dependency version conflicts.

### Executing this runbook

```shell
gcpdiag runbook dataproc/spark-job-failures \
  -p project_id=value \
  -p job_id=value \
  -p dataproc_job_id=value \
  -p region=value \
  -p zone=value \
  -p service_account=value \
  -p cross_project=value \
  -p stackdriver=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `job_id` | False | None | str | The Job ID of the resource under investigation |
| `dataproc_job_id` | True | None | str | The Job ID of the resource under investigation |
| `region` | True | None | str | Dataproc job/cluster Region |
| `zone` | False | None | str | Dataproc cluster Zone |
| `service_account` | False | None | str | Dataproc cluster Service Account used to create the resource |
| `cross_project` | False | None | str | Cross Project ID, where service account is located if it is not in the same project as the Dataproc cluster |
| `stackdriver` | False | False | str | Checks if stackdriver logging is enabled for further troubleshooting |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Job Start](/runbook/steps/dataproc/job-start)

  - [Job Details Dependency Gateway](/runbook/steps/dataproc/job-details-dependency-gateway)

  - [Check If Job Failed](/runbook/steps/dataproc/check-if-job-failed)

  - [Check Task Not Found](/runbook/steps/dataproc/check-task-not-found)

  - [Check Master Oom](/runbook/steps/dataproc/check-master-oom)

  - [Check Worker Oom](/runbook/steps/dataproc/check-worker-oom)

  - [Check Sw Preemption](/runbook/steps/dataproc/check-sw-preemption)

  - [Check Worker Disk Usage Issue](/runbook/steps/dataproc/check-worker-disk-usage-issue)

  - [Check Port Exhaustion](/runbook/steps/dataproc/check-port-exhaustion)

  - [Check Killing Orphaned Application](/runbook/steps/dataproc/check-killing-orphaned-application)

  - [Check Python Import Failure](/runbook/steps/dataproc/check-python-import-failure)

  - [Check Shuffle Service Kill](/runbook/steps/dataproc/check-shuffle-service-kill)

  - [Check Gc Pause](/runbook/steps/dataproc/check-gc-pause)

  - [Check Yarn Runtime Exception](/runbook/steps/dataproc/check-yarn-runtime-exception)

  - [Check Job Throttling](/runbook/steps/dataproc/check-job-throttling)

  - [Check Gcs Connector](/runbook/steps/dataproc/check-gcs-connector)

  - [Check Shuffle Failures](/runbook/steps/dataproc/check-shuffle-failures)

  - [Check Stackdriver Setting](/runbook/steps/dataproc/check-stackdriver-setting)

  - [Check Cluster Version](/runbook/steps/dataproc/check-cluster-version)

  - [Check Permissions](/runbook/steps/dataproc/check-permissions)

  - [Check Cluster Network Connectivity](/runbook/steps/dataproc/check-cluster-network-connectivity)

  - [Check Bq Connector](/runbook/steps/dataproc/check-bq-connector)

  - [Spark Job End](/runbook/steps/dataproc/spark-job-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
