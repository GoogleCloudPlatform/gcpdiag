# Generating builds history data.
## TLDR
After initializing the repository to generate build history run
`make run-builds` once and only once.

## Explanation

Terraform does not allow to run builds since it is not a resource,
but imperative procedure. Also there is no way to clear builds history, so it is
important that running builds happens only once.

If you want to add some data to build history, and you need to retry build
several times to get desired outcome, then after you got to desired effect
either run `terraform destroy` and initialize a new project or manualy remove
older builds from json dump.
