# Errors on uploading logs to bucket with retention policy.
steps:
- name: gcr.io/cloud-builders/docker
  args: ["ps"]
logsBucket: 'gs://${bucket}'
