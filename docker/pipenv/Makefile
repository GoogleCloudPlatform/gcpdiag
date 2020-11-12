VERSION=0.3
IMAGE=us-docker.pkg.dev/gcp-doctor-repo/dev/gcp-doctor-pipenv

build:
	docker build -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
