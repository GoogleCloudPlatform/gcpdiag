#!/bin/bash

set -e
set -x

PATH="${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor/bin:$HOME/.local/bin:$PATH"
cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"

pipenv-dockerized run pipenv install --dev
pipenv-dockerized run make test
pipenv-dockerized run make coverage-report
pipenv-dockerized run make kokoro-publish-test
#
#echo $KOKORO_KEYSTORE_DIR
#ls -lR $KOKORO_KEYSTORE_DIR
rm dist/gcp-doctor
#echo "FOOBAR" >dist/gcp-doctor-0.8
#echo "FOOBAR" >dist/gcp-doctor-0.8-test
#echo "BAZBAZ" >dist/gcp-doctor-0.9-test
#chmod +x dist/gcp-doctor-0.9-test
#ln -s gcp-doctor-0.9-test dist/gcp-doctor-0.9-symlink
mkdir dist/testdir
echo "BLABLA" >dist/testdir/blabla

ls -lR dist
