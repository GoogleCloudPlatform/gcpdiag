#!/bin/sh

IMAGE=us-docker.pkg.dev/gcpdiag-repo/devel/gcpdiag-hugo:0.1
SUPPORTED_RUNTIME="docker podman"

if [ "$#" -eq 0 ]; then
  ARGS="--themesDir=/themes"
elif [ "$1" = "server" ]; then
  shift
  ARGS="server --themesDir=/themes --bind 0.0.0.0 -b http://localhost:1313 $@"
else
  ARGS="$@ --themesDir=/themes"
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

exec "$RUNTIME" run $USE_TTY \
  --rm \
  -u "$(id -u):$(id -g)" \
  -e "USER=$(id -n -u)" \
  -e "GROUP=$(id -n -g)" \
  -e "SHELL=/bin/bash" \
  -e HOME -e LANG \
  -e GOOGLE_APPLICATION_CREDENTIALS \
  -v "$(pwd):/src" \
  -v "$HOME/.config/gcloud:$HOME/.config/gcloud" \
  -p 1313:1313 \
  $IMAGE \
  hugo \
  $ARGS
