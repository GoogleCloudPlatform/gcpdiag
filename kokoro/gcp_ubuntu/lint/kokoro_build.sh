#!/bin/bash

set -e

if [[ -n "$KOKORO_ARTIFACTS_DIR" ]]; then
  cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"
fi

pylintrc_path=$(pwd)/kokoro/gcp_ubuntu/lint/pylintrc_google

pyenv global 3.6.1
. venv-activate
python -m pip install -r requirements.txt
python -m pip install pylint>=2.2
find gcp_doctor -name "*.py" -print0 | xargs -0 python -m pylint --rcfile="$pylintrc_path"
