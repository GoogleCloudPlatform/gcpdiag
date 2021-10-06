BIN_DIR=../../bin
VERSION=$(shell sed -n 's/^current_version\s*=\s*//p' <../../.bumpversion.cfg)
ifneq (,$(findstring test,$(VERSION)))
REPO_NAME=test
else
REPO_NAME=release
endif
IMAGE=us-docker.pkg.dev/gcpdiag-repo/$(REPO_NAME)/gcpdiag
RELEASE_BUCKET_NAME=gcpdiag
WRAPPER_BUCKET_NAME=gcpdiag-web
SHELL=/bin/bash

OBJECT_NAME_RELEASE_VERSION=release-version
WRAPPER_VERSION=0.6
VERSION_FILE_URL=https://storage.googleapis.com/gcpdiag/$(OBJECT_NAME_RELEASE_VERSION)

build:
	make -C ../.. tarfile
	rm -rf dist
	mkdir dist
	cd dist && tar -xf ../../../dist/gcpdiag-$(VERSION).tar.gz --strip 1
	chmod -R a+rX dist
	docker build --pull -t $(IMAGE):$(VERSION) .
	rm -rf dist

push:
	docker push $(IMAGE):$(VERSION)

# We mark in Cloud Storage what version clients should use by default. This is
# much faster than running 'docker pull' everytime (and also avoids the bad
# practice of using generic docker image tags like 'default')
update-default:
	echo -e "DOCKER_IMAGE=$(IMAGE)\nDOCKER_IMAGE_VERSION=$(VERSION)\nWRAPPER_VERSION=$(WRAPPER_VERSION)" | gsutil -h "Content-Type: text/plain" -h "Cache-Control: max-age=300" cp - "gs://$(RELEASE_BUCKET_NAME)/$(OBJECT_NAME_RELEASE_VERSION)"

upload-wrapper:
	# only update docker wrapper script if this version is newer ($(WRAPPER_VERSION))
	@CUR_WRAPPER_VERSION=$$(curl -sf $(VERSION_FILE_URL) | grep WRAPPER_VERSION | sed -e 's/.*=//'); \
	  if [ "$$CUR_WRAPPER_VERSION" != "$(WRAPPER_VERSION)" ]; then \
	    echo "uploading new wrapper."; \
	    gsutil -h "Content-Type: text/plain" -h "Cache-Control: max-age=300" cp $(BIN_DIR)/gcpdiag-dockerized "gs://$(WRAPPER_BUCKET_NAME)/gcpdiag.sh"; \
	  else \
	    echo "wrapper unchanged."; \
	  fi
