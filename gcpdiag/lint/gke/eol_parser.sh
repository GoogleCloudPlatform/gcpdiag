#!/bin/bash

# Parses the public GKE Schedule page and extratct EOL (end-of-life) dates
# for currently available GKE versions

curl -s https://cloud.google.com/kubernetes-engine/docs/release-schedule |
  sed -n '/<tbody>/,/<\/tbody>/p' |
  grep -vE 'tbody>|tr>' |
  sed -e 's/<\/td.*//g' -e 's/<sup.*//g' -e 's/^.*>//g' |
  tr '\n' ' ' |
  (read -a GKE_REL

echo '# Auto-generated, DO NOT edit manually'
echo '# Use `make gke-eol-file` from the top level directory'

len=${#GKE_REL[@]}
for (( i=0; i<$len; i+=9 ))
do
  echo "'${GKE_REL[$i]}':"
  echo "  oss_release: ${GKE_REL[$((i + 1))]}"
  echo "  rapid_avail: ${GKE_REL[$((i + 2))]}"
  echo "  regular_avail: ${GKE_REL[$((i + 4))]}"
  echo "  stable_avail: ${GKE_REL[$((i + 6))]}"
  echo "  eol: ${GKE_REL[$((i + 8))]}"
done)
