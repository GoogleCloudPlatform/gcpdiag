BIN_DIR=../../bin
VERSION:=$(shell cd ../.. && make version)
IMAGE=us-docker.pkg.dev/gcp-doctor-repo/release/gcp-doctor
BUCKET_NAME=gcp-doctor
OBJECT_NAME_DEFAULT_VERSION=default-version

build:
	make -C ../.. dist
	rm -rf dist
	mkdir dist
	cd dist && tar -xf ../../../dist/gcp-doctor-$(VERSION).tar.gz --strip 1
	chmod -R a+rX dist
	docker build -t $(IMAGE):$(VERSION) .
	rm -rf dist

push:
	docker push $(IMAGE):$(VERSION)

# We mark in Cloud Storage what version clients should use by default. This is
# much faster than running 'docker pull' everytime (and also avoids the bad
# practice of using generic docker image tags like 'default')
update-default:
	$(BIN_DIR)/curl-wrap.sh -X POST --data '$(VERSION)' \
	  -H "Content-Type: text/plain" \
	  "https://storage.googleapis.com/upload/storage/v1/b/$(BUCKET_NAME)/o?uploadType=media&name=$(OBJECT_NAME_DEFAULT_VERSION)"

upload-wrapper:
	$(BIN_DIR)/curl-wrap.sh -X POST --data-binary @$(BIN_DIR)/gcp-doctor-dockerized \
	  -H "Content-Type: text/plain" \
	  "https://storage.googleapis.com/upload/storage/v1/b/$(BUCKET_NAME)/o?uploadType=media&name=gcp-doctor.sh"
