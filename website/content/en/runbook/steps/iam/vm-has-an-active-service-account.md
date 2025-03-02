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

Service account: {sa} is deleted

### Failure Remediation

Service account: {sa} has been deleted. If you want to restore a deleted service account,
you can undelete it, if it's been
30 days or less since you deleted the service account.
After 30 days, IAM permanently removes the service account. Google Cloud cannot recover the
service account after it is permanently removed, even if you file a support request.
Follow [1] to and [2] to verify service account is deleted.
[1] <https://cloud.google.com/iam/docs/service-accounts-delete-undelete#deleting>
[2] <https://cloud.google.com/iam/docs/service-accounts-delete-undelete#undeleting>

### Success Reason

Service account: {sa} is currently in active

### Uncertain Reason

Can't find service account {sa}

### Uncertain Remediation

The service account `{sa}` could not be automatically detected or validated for its status (e.g., active, disabled, or deleted).

- To manually verify the service account, refer to the [documentation for listing and checking service accounts](https://cloud.google.com/iam/docs/service-accounts-list-edit#listing).
- For information on deleted service accounts, see [deleted service account details](https://cloud.google.com/iam/docs/service-accounts-delete-undelete#deleting).
- If the service account was deleted, review [how to undelete a service account](https://cloud.google.com/iam/docs/service-accounts-delete-undelete#undeleting) to recover it if feasible.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
