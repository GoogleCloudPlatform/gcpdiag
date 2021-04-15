#!/bin/bash

set -e
set -x

PATH="${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor/bin:$HOME/.local/bin:$PATH"
cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"

pipenv-dockerized run pipenv install --dev
pipenv-dockerized run make test
pipenv-dockerized run make coverage-report
pipenv-dockerized run make kokoro-publish-release
#
#echo $KOKORO_KEYSTORE_DIR
#ls -lR $KOKORO_KEYSTORE_DIR

# make sure that the files are not group-writable, because
# otherwise all mdb/gcp-doctor-users would be allowed, and this
# is not permitted (more than 500 users)
chmod -R go-w dist

echo "FOOBAR" >dist/gcp-doctor-0.8
echo "FOOBAR" >dist/gcp-doctor-0.8-test
echo "BAZBAZ" >dist/gcp-doctor-0.9-test
chmod +x dist/gcp-doctor-0.9-test
ln -s gcp-doctor-0.9-test dist/gcp-doctor-0.9-symlink
mkdir dist/testdir
echo "BLABLA" >dist/testdir/blabla
ln -s blabla dist/testdir/blabla-link

ls -lR ${KOKORO_ARTIFACTS_DIR}
