VERSION=0.7
IMAGE=us-docker.pkg.dev/gcpdiag-repo/devel/gcpdiag-pipenv

build:
	docker build --pull --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
