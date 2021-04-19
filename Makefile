VERSION=0.15-test
DIST_NAME=gcp-doctor-$(VERSION)
SHELL=/bin/bash

test:
	coverage run --include='gcp_doctor/*' -m pytest --forked

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

release:
	# Make sure we are using the latest submitted code.
	git fetch
	git checkout origin/master
	# Remove '-test' in the version.
	# Note: this will fail if we have already a release tag, in which case
	# you should first increase the minor version with a code review.
	bumpversion --commit --tag --tag-message "Release v{new_version}" release
	# push to the release branch and tag the release
	git merge -s ours origin/release
	git push origin HEAD:release
	git push --tags
	# increment the version (and add back '-test')
	bumpversion --commit minor
	git push origin HEAD:refs/for/master

### Kokoro-specific (do not run interactively) ###

kokoro-build: build
	# create the directory structure that we want in x20
	mkdir -p dist/x20/v$(VERSION)
	mv dist/gcp-doctor dist/x20/v$(VERSION)
	ln -s v$(VERSION) dist/x20/latest
	# make sure that the files are not group-writable, because
	# otherwise all mdb/gcp-doctor-users would be allowed, and this
	# is not permitted (more than 500 users)
	chmod -R go-w dist/x20

.PHONY: test coverage-report version build bump-version tarfile release kokoro-build
