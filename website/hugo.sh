#!/bin/sh

IMAGE=us-docker.pkg.dev/gcpdiag-repo/devel/gcpdiag-hugo:0.1

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

docker run $USE_TTY \
  --rm \
  -u "$(id -u):$(id -g)" \
  -e "USER=$(id -n -u)" \
  -e "GROUP=$(id -n -g)" \
  -e "SHELL=/bin/bash" \
  -e HOME -e LANG \
  -v "$(pwd):/src" \
  -v "$HOME/.config/gcloud:$HOME/.config/gcloud" \
  -p 1313:1313 \
  $IMAGE \
  hugo \
  $ARGS
