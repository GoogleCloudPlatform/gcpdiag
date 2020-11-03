#!/bin/bash

set -e
set -x

. venv-activate

pip install -r requirements.txt
pip install pytest
pytest
