---
title: "gcpdiag Privacy Policy"
linkTitle: "Privacy Policy"
type: docs
hide_summary: true
---

## gcpdiag tool

### Data collected via public APIs

gcpdiag is a command-line tool that uses credentials provided by you (via
service account key or application default credentials) to access your data in
Google Cloud Platform via public APIs.

The collected data is never stored or transmitted anywhere except on the
environment where you run it:

- gcpdiag caches data (credentials and certain API call results) under
  `$HOME/.cache/gcpdiag` or `$HOME/.cache/gcpdiag-dockerized`, which
  you can delete at any time.

- gcpdiag will display findings to stdout/stderr (console) or to local files
  you specify.

In other words: the data collected by gcpdiag always stays with you.

### User-agent

The gcpdiag command-line tool sets a specific User-agent string for the GCP API
calls, which makes it possible to identify them as originating from the gcpdiag
tool. The [Google Cloud Privacy
Notice](https://cloud.google.com/terms/cloud-privacy-notice) describes how
Google collects and processes personal information in relation to Google Cloud
Platform and Google’s other Cloud Services.

## Website

For the website http://gcpdiag.dev, the privacy policy at
https://policies.google.com/privacy applies.
