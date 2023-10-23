#!/bin/sh

# Checks if gcpdiag/lint/gke/eol.yaml file contains the up to date list of
# GKE Releases with corresponding EOL (end-of-life) dates

if ! ./gcpdiag/lint/gke/eol_parser.sh | diff - gcpdiag/lint/gke/eol.yaml > /dev/null
then
  echo 'GKE eol.yaml file is outdated. Please run `make gke-eol-file` from the top level directory'
  exit 1
fi
