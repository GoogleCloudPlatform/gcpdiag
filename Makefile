VERSION=0.10-test
DIST_NAME=gcp-doctor-$(VERSION)
SHELL=/bin/bash

test:
	coverage run --include='gcp_doctor/*' -m pytest

coverage-report:
	coverage report -m --omit="*/*_test.py,*/*_stub.py"

version:
	@echo $(VERSION)

build:
	pyinstaller --workpath=.pyinstaller.build pyinstaller.spec

bump-version:
	bumpversion --commit minor

publish-test: build
	# make sure that the version has "-test" in it
	@if [[ ! "$(VERSION)" =~ -test ]]; then \
	  echo "$(VERSION) doesn't look like a test version."; \
	  exit 1; fi
	# x20
	cp dist/gcp-doctor /google/data/rw/teams/gcp-doctor/test/gcp-doctor-$(VERSION)
	# docker
	make -C docker/gcp-doctor build
	make -C docker/gcp-doctor push

dist:
	# TODO(dwes): replace with something based on setuptools?
	rm -rf dist-tmp
	mkdir -p dist-tmp/$(DIST_NAME)
	cp Pipfile Pipfile.lock README.md dist-tmp/$(DIST_NAME)
	cp gcp-doctor dist-tmp/$(DIST_NAME)
	chmod +x dist-tmp/$(DIST_NAME)/gcp-doctor
	cp --parents gcp_doctor/queries/client_secrets.json dist-tmp/$(DIST_NAME)
	find gcp_doctor -name '*.py' -exec cp --parents '{}' dist-tmp/$(DIST_NAME) ';'
	chmod -R a+rX dist-tmp
	mkdir -p dist
	tar -C dist-tmp -czf dist/gcp-doctor-$(VERSION).tar.gz --owner=0 --group=0 gcp-doctor-$(VERSION)
	rm -rf dist-tmp

### Kokoro-specific (do not run interactively) ###

kokoro-bump-release:
	# remove "test" from the version and create a git tag
	bumpversion --tag release
	# push tag
	git push --tags

kokoro-publish-release: kokoro-bump-release build
	# x20
	cp dist/gcp-doctor /google/data/rw/teams/gcp-doctor/release/gcp-doctor-$(VERSION)
	# docker
	make -C docker/gcp-doctor build
	make -C docker/gcp-doctor push
	# increase the minor version so that future test releases use the next version
	bumpversion --commit minor
	git push

kokoro-update-default:
	# x20
	ln -sf ../releases/gcp-doctor-$(VERSION) /google/data/rw/teams/gcp-doctor/bin/gcp-doctor
	# docker
	make -C docker/gcp-doctor upload-wrapper
	make -C docker/gcp-doctor update-default

.PHONY: test coverage-report version build bump-version publish-test dist
