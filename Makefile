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
	rm -f dist/gcp-doctor
	pyinstaller --workpath=.pyinstaller.build pyinstaller.spec

bump-version:
	bumpversion --commit minor

tarfile:
	# TODO: replace with something based on setuptools?
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

kokoro-verify-user:
	@if [[ "$$USER" != "kbuilder" ]]; then \
	  echo "this must be run by kokoro (kbuilder)" >&2; \
	  exit 1; fi

kokoro-bump-release: kokoro-verify-user
	git config user.email "noreply+kokoro@google.com"
	git config user.name "Kokoro release job"
	# remove "test" from the version and create a git tag
	bumpversion --verbose --tag release
	# push tag
	git push --tags
	# increment test version
	bumpversion --commit minor
	git push

kokoro-build: build
	# create the directory structure that we want in x20
	mkdir dist/v$(VERSION)
	mv dist/gcp-doctor dist/v$(VERSION)
	ln -s v$(VERSION) dist/latest
	# make sure that the files are not group-writable, because
	# otherwise all (internal) would be allowed, and this
	# is not permitted (more than 500 users)
	chmod -R go-w dist

kokoro-update-default:
	# x20
	ln -sf ../releases/gcp-doctor-$(VERSION) /google/data/rw/teams/gcp-doctor/bin/gcp-doctor
	# docker
	make -C docker/gcp-doctor upload-wrapper
	make -C docker/gcp-doctor update-default

.PHONY: test coverage-report version build bump-version publish-test tarfile
