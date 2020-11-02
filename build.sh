#!/bin/bash

set -e

. venv-activate

pip install -r requirements.txt
pip install pytest
pytest
