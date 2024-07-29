---
title: "composer/Encryption Config Checker"
linkTitle: "Encryption Config Checker"
weight: 3
type: docs
description: >
  Checks the permissions of the KMS key used for encryption in Composer env.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This class performs the following checks:

  1. **CMEK Configuration:** Verifies if Customer-Managed Encryption Keys (CMEK)
  are enabled for the selected Cloud Composer environment. CMEK provides
  enhanced security by allowing you to manage encryption keys within your own
  Google Cloud project.

  2. **IAM Permissions:** If CMEK is enabled, it checks whether the necessary
  Google Cloud service accounts have the required permissions
  (`cloudkms.cryptoKeyEncrypterDecrypter`) to use the KMS key. These permissions
  are crucial for successful encryption and decryption operations.

  Attributes: None

  Methods:
      check_kms_key_permissions(project_id, key_name):
          Validates the IAM permissions of the specified KMS key.

      execute():
          Retrieves the Cloud Composer environment configuration and initiates
          the KMS key checks.

  Raises:
      AttributeError: If the KMS key configuration is missing or unexpected.
      Exception: For any other unexpected errors encountered during the checks.

  Note:
      This class assumes that the Cloud Composer environment configuration is
      available in the `op` object (presumably an operation context).

  Example Usage:
      checker = EncryptionConfigChecker()
      checker.execute()



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
