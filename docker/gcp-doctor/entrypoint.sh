#!/bin/bash

# If the container is running as non-root (as it should), make sure that we have
# an entry for this UID and GID in passwd and group.
if [[ $UID -ne 0 ]]; then
  GID=$(id -g)
  USER=${USER:-local}
  GROUP=${GROUP:-local}
  echo "${USER}:x:${UID}:${GID}::${HOME}:/bin/bash" >>/etc/passwd
  echo "${GROUP}:x:${GID}:" >>/etc/group
fi

# activate the venv for gcp-doctor
. /opt/gcp-doctor/.venv/bin/activate

exec "$@"
