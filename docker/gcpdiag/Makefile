BIN_DIR=../../bin
VERSION=$(shell sed -n 's/^current_version\s*=\s*//p' <../../.bumpversion.cfg)
ifneq (,$(findstring test,$(VERSION)))
REPO_NAME=staging
else
REPO_NAME=release
endif
IMAGE=us-docker.pkg.dev/gcpdiag-dist/$(REPO_NAME)/gcpdiag
RELEASE_BUCKET_NAME=gcpdiag-dist
SHELL=/bin/bash

OBJECT_NAME_RELEASE_VERSION=release-version
WRAPPER_VERSION=0.11
VERSION_FILE_URL=https://storage.googleapis.com/$(RELEASE_BUCKET_NAME)/$(OBJECT_NAME_RELEASE_VERSION)

build:
	make -C ../.. tarfile
	rm -rf dist
	mkdir dist
	cd dist && tar -xf ../../../dist/gcpdiag-$(VERSION).tar.gz --strip 1
	cd dist && gcloud storage cp gs://check-gke-ingress-push/kubectl-check_gke_ingress ./ && chmod +x kubectl-check_gke_ingress
	chmod -R a+rX dist
	docker build --pull -t $(IMAGE):$(VERSION) .
	rm -rf dist

push:
	docker push $(IMAGE):$(VERSION)

# We mark in Cloud Storage what version clients should use by default. This is
# much faster than running 'docker pull' every time (and also avoids the bad
# practice of using generic docker image tags like 'default')
update-default:
	echo -e "DOCKER_IMAGE=$(IMAGE)\nDOCKER_IMAGE_VERSION=$(VERSION)\nWRAPPER_VERSION=$(WRAPPER_VERSION)" | gcloud storage cp --content-type="text/plain" --cache-control="max-age=300" - "gs://$(RELEASE_BUCKET_NAME)/$(OBJECT_NAME_RELEASE_VERSION)"
