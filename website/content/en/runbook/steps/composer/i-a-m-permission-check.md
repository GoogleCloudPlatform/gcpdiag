---
title: "composer/I A M Permission Check"
linkTitle: "I A M Permission Check"
weight: 3
type: docs
description: >
  Verifies IAM permissions for Google Cloud Composer service accounts.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This class performs a comprehensive check of the IAM (Identity and Access
  Management)
  permissions assigned to essential service accounts utilized by Google Cloud
  Composer.
  It ensures that these accounts possess the necessary roles to interact with
  Google
  Cloud resources and perform their intended functions within the Composer
  environment.

  Attributes: None

  Methods:
      execute(self):
          Initiates the IAM permission check for all specified service accounts.
      _check_iam_permissions(self, project_id, service_account, required_role,
      account_description):
          Helper function to verify IAM permissions for a specific service
          account and role.
      Raises:
      Exception: If an error occurs during the IAM permission check process,
      it's logged and
                 an appropriate failure message is added to the runbook
                 operation.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
