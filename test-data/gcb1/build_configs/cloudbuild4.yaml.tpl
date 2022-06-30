# Successfully uploads logs to bucket with retention policy.
steps:
- name: gcr.io/cloud-builders/docker
  args: ["ps"]
logsBucket: 'gs://${bucket}'
options:
  logging: GCS_ONLY
  logStreamingOption: STREAM_OFF
