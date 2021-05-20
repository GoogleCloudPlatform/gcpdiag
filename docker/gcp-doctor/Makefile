BIN_DIR=../../bin
VERSION=0.17-test
IMAGE=us-docker.pkg.dev/gcp-doctor-repo/google-internal/gcp-doctor
BUCKET_NAME=gcp-doctor
SHELL=/bin/bash

# "default-version" was the old name where we only put the version in the file
# we changed to "release-version" with a new format: KEY=VALUE pairs (shell
# script-sourceable)
OBJECT_NAME_RELEASE_VERSION=release-version
WRAPPER_VERSION=0.4
VERSION_FILE_URL=https://storage.googleapis.com/gcp-doctor/$(OBJECT_NAME_RELEASE_VERSION)

build:
	make -C ../.. tarfile
	rm -rf dist
	mkdir dist
	cd dist && tar -xf ../../../dist/gcp-doctor-$(VERSION).tar.gz --strip 1
	# also copy google-internal modules, considering that this is published
	# ona google-internal repo (accessible only for google.com
	# organization)
	mkdir -p dist/gcp_doctor_google_internal
	cp ../../gcp_doctor_google_internal/{cta_client,metric_pb2}.py dist/gcp_doctor_google_internal
	# compatibility with old docker image:
	cd dist && mkdir bin && ln -s ../gcp-doctor bin/gcp-doctor
	chmod -R a+rX dist
	docker build --pull -t $(IMAGE):$(VERSION) .
	rm -rf dist

push:
	docker push $(IMAGE):$(VERSION)

# We mark in Cloud Storage what version clients should use by default. This is
# much faster than running 'docker pull' everytime (and also avoids the bad
# practice of using generic docker image tags like 'default')
update-default:
	echo -e "DOCKER_IMAGE=$(IMAGE)\nDOCKER_IMAGE_VERSION=$(VERSION)\nWRAPPER_VERSION=$(WRAPPER_VERSION)" | gsutil -h "Content-Type: text/plain" -h "Cache-Control: max-age=300" cp - "gs://$(BUCKET_NAME)/$(OBJECT_NAME_RELEASE_VERSION)"

upload-wrapper:
	# only update docker wrapper script if this version is newer ($(WRAPPER_VERSION))
	@CUR_WRAPPER_VERSION=$$(curl -sf $(VERSION_FILE_URL) | grep WRAPPER_VERSION | sed -e 's/.*=//'); \
	  if [ "$$CUR_WRAPPER_VERSION" != "$(WRAPPER_VERSION)" ]; then \
	    echo "uploading new wrapper."; \
	    gsutil -h "Content-Type: text/plain" -h "Cache-Control: max-age=300" cp $(BIN_DIR)/gcp-doctor-dockerized "gs://$(BUCKET_NAME)/gcp-doctor.sh"; \
	  else \
	    echo "wrapper unchanged."; \
	  fi
