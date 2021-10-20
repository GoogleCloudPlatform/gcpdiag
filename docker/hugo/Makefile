VERSION=0.1
IMAGE=us-docker.pkg.dev/gcpdiag-repo/devel/gcpdiag-hugo

build:
	docker build --pull --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
