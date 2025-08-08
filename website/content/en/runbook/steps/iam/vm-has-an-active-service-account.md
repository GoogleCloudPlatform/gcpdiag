---
title: "iam/Vm Has An Active Service Account"
linkTitle: "Vm Has An Active Service Account"
weight: 3
type: docs
description: >
  Investigates if a VM's service account is active.
---

**Product**: [Identity and Access Management (IAM)](https://cloud.google.com/iam)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the specified service account is neither disabled nor deleted.
  It verifies the existence of the service account and its active status within
  the specified project.

  Attributes:
    template (str): Template identifier for reporting the service account status.
    service_account (str, optional): The email address of the service account to check.
                                     If not provided, it is obtained from the operation's context.
    project_id (str, optional): The ID of the Google Cloud project within which to check
                                the service account. If not provided, it is obtained from
                                the operation's context.

### Failure Reason

Service account {sa} is deleted.

### Failure Remediation

Service account {sa} has been deleted. Deleted service accounts can be undeleted within 30 days of deletion [2]. After 30 days, IAM permanently removes the service account, and it cannot be recovered.
Refer to [1] for details on deleting service accounts and [2] for undeleting them.
[1] <https://cloud.google.com/iam/docs/service-accounts-delete-undelete#deleting>
[2] <https://cloud.google.com/iam/docs/service-accounts-delete-undelete#undeleting>

### Success Reason

Service account {sa} is active.

### Uncertain Reason

Could not find service account {sa}.

### Uncertain Remediation

Could not determine the status (e.g., active, disabled, or deleted) for service account `{sa}`.

- To manually verify the service account, refer to the [documentation for listing and checking service accounts](https://cloud.google.com/iam/docs/service-accounts-list-edit#listing).
- For information on deleted service accounts, see [deleted service account details](https://cloud.google.com/iam/docs/service-accounts-delete-undelete#deleting).
- If the service account was deleted, review [how to undelete a service account](https://cloud.google.com/iam/docs/service-accounts-delete-undelete#undeleting) to recover it if feasible.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
