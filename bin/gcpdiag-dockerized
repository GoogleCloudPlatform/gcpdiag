#!/bin/bash
set -e
THIS_WRAPPER_VERSION=0.8
SUPPORTED_RUNTIME="docker podman"

eval $(curl -sf https://storage.googleapis.com/gcpdiag/release-version|grep -Ei '^\w*=[0-9a-z/\._-]*$')

# Test whether 1st arg is greater than or equal to the 2nd, when compared as version numbers (bash-only)
version_ge () {
  # Note: implementation is rather crude and will treat missing numbers as `0`
  # so e.g. "1" and "1.0.0" compare equal; even worse, "..1" is accepted and
  # less than "0.0.2", and the empty string is equal to "0.0"
  local -a V1=(${1//./ })
  local -a V2=(${2//./ })
  if (( ${#V1[@]} > ${#V2[@]} )); then
    local -i len=${#V1[@]}
  else
    local -i len=${#V2[@]}
  fi
  for i in $(seq 0 ${len}); do
    if (( "${V1[$i]:-0}" < "${V2[$i]:-0}")); then
      return 1  # V1[i] < V2[i]
    fi
  done
  return 0  # V1 >= V2
}

# Check this script version and compare with the minimum required version
# defined in the release-version file. This allows us to force an upgrade
# of the wrapper script.
if ! version_ge "$THIS_WRAPPER_VERSION" "$WRAPPER_VERSION"; then
  echo
  echo "## ERROR:"
  echo "## This gcpdiag wrapper script is obsolete (version $THIS_WRAPPER_VERSION, minimum required: $WRAPPER_VERSION)."
  echo "## Please update the wrapper script to the latest version as follows:"
  echo
  echo "curl https://gcpdiag.dev/gcpdiag.sh >gcpdiag"
  echo "chmod +x gcpdiag"
  echo
  exit 1
fi

[ -t 0 ] && USE_TTY="-it" || USE_TTY=""
# Note: for some reason sometimes docker creates the container-path in the host
# and this can result in ~/.cache/gcpdiag being owned by root. Workaround
# this issue by creating ~/.cache/gcpdiag as well first, so that the
# ownership is correct.
mkdir -p "$HOME/.cache/gcpdiag" \
         "$HOME/.cache/gcpdiag-dockerized" \
         "$HOME/.config/gcloud"

# Set RUNTIME based on available container runtime cmd
for r in $SUPPORTED_RUNTIME; do
  if command -v "$r" >/dev/null; then
    RUNTIME="$r"
    break
  fi
done

if [ -z "$RUNTIME" ]; then
  >&2 echo "No container runtime found - supported: $SUPPORTED_RUNTIME"
  exit 1
fi

if [ "$RUNTIME" = podman ]; then
  export PODMAN_USERNS=keep-id
fi

exec "$RUNTIME" run "$USE_TTY" \
  --rm \
  -u "$(id -u):$(id -g)" \
  -e "USER=$(id -n -u)" \
  -e "GROUP=$(id -n -g)" \
  -e "SHELL=/bin/bash" \
  -e HOME -e LANG -e GOOGLE_AUTH_TOKEN -e CLOUD_SHELL \
  -v "$HOME/.cache/gcpdiag-dockerized:$HOME/.cache/gcpdiag" \
  -v "$HOME/.config/gcloud:$HOME/.config/gcloud" \
  "$DOCKER_IMAGE:$DOCKER_IMAGE_VERSION" /opt/gcpdiag/bin/gcpdiag "$@"
