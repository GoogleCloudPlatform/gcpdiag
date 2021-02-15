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
	echo "$(VERSION)" | gsutil  -h "Cache-Control: max-age=300" cp - "gs://$(BUCKET_NAME)/$(OBJECT_NAME_DEFAULT_VERSION)"

upload-wrapper:
	gsutil  -h "Cache-Control: max-age=300" cp $(BIN_DIR)/gcp-doctor-dockerized "gs://$(BUCKET_NAME)/gcp-doctor.sh"
