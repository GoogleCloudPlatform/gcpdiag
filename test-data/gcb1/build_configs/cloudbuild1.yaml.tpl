# Builds an image but errors on uploading it to artifact registry due to lack of
# permissions.
steps:
- name: gcr.io/cloud-builders/docker
  args: ["tag", "gcr.io/cloud-builders/docker", "${image}"]
images:
- ${image}
serviceAccount: '${sa}'
options:
  logging: CLOUD_LOGGING_ONLY
