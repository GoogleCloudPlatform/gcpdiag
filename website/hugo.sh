#!/bin/bash
set -eu # set bash strict mode to catch subtle bugs

IMAGE=us-docker.pkg.dev/gcpdiag-dist/common/gcpdiag-hugo:0.3
SUPPORTED_RUNTIME="docker podman"

# If no arguments are provided, default to 'server' in interactive shells
# and 'build' in non-interactive (CI/CD) shells.
if [ "$#" -eq 0 ]; then
  if [ -t 0 ]; then
    set -- "server"
  else
    set -- "build"
  fi
fi

# If the command is 'server', add default arguments for local development
if [ "$1" = "server" ]; then
  shift
  set -- "server" "--bind" "0.0.0.0" "-b" "http://localhost:1313" "$@"
fi

mkdir -p "$HOME/.config/gcloud"

[ -t 0 ] && USE_TTY="-it"

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

exec "$RUNTIME" run ${USE_TTY:-} \
  --rm \
  -u "$(id -u):$(id -g)" \
  -e "USER=$(id -n -u)" \
  -e "GROUP=$(id -n -g)" \
  -e "SHELL=/bin/bash" \
  -e HOME -e LANG \
  -e GOOGLE_APPLICATION_CREDENTIALS \
  -w /src \
  -v "$(pwd):/src" \
  -v "$HOME/.config/gcloud:$HOME/.config/gcloud" \
  -p 1313:1313 \
  "$IMAGE" \
  "$@"
