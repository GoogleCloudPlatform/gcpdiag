VERSION=0.5
IMAGE=us-docker.pkg.dev/gcp-doctor-repo/public/gcp-doctor-pipenv

build:
	docker build --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
