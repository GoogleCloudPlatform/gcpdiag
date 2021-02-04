VERSION=0.4
IMAGE=us-docker.pkg.dev/gcp-doctor-repo/dev/gcp-doctor-pipenv

build:
	docker build --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
