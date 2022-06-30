VERSION=0.7
IMAGE=us-docker.pkg.dev/gcpdiag-dist/common/gcpdiag-pipenv-python-3.7

build:
	docker build --pull --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
