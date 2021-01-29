#!/bin/sh

# send a curl request with gcloud default app credentials

exec curl \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  "$@"
