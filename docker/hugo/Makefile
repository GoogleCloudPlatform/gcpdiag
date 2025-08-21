VERSION=0.3
IMAGE=us-docker.pkg.dev/gcpdiag-dist/common/gcpdiag-hugo

build:
	docker build --pull --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
