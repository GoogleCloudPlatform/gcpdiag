#!/bin/bash
set -e
THIS_WRAPPER_VERSION=0.8
SUPPORTED_RUNTIME="docker podman"

eval $(curl -sf https://storage.googleapis.com/gcpdiag/release-version|grep -Ei '^\w*=[0-9a-z/\._-]*$')
if [[ $THIS_WRAPPER_VERSION != "$WRAPPER_VERSION" ]]; then
  echo
  echo "## ERROR:"
  echo "## This gcpdiag wrapper script is obsolete ($THIS_WRAPPER_VERSION, newest: $WRAPPER_VERSION)."
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
