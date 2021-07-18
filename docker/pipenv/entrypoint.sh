#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# If the container is running as non-root (as it should), make sure that we have
# an entry for this UID and GID in passwd and group.
if [[ $UID -ne 0 ]]; then
  GID=$(id -g)
  USER=${USER:-local}
  GROUP=${GROUP:-local}
  echo "${USER}:x:${UID}:${GID}::${HOME}:/bin/bash" >>/etc/passwd
  echo "${GROUP}:x:${GID}:" >>/etc/group
fi
exec "$@"
