VERSION=0.6
IMAGE=us-docker.pkg.dev/gcp-doctor-repo/public/gcp-doctor-pipenv

build:
	docker build --pull --no-cache -t $(IMAGE):$(VERSION) .

push:
	docker push $(IMAGE):$(VERSION)
