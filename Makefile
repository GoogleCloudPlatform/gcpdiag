VERSION=$(shell sed -n 's/^current_version\s*=\s*//p' <.bumpversion.cfg)
DIST_NAME=gcpdiag-$(VERSION)
SHELL=/bin/bash

test:
	pytest -o log_level=DEBUG --cov-config=.coveragerc --cov=gcpdiag --forked

test_async_api:
	python -m unittest gcpdiag.async_queries.api.api_slowtest

test-mocked:
	# run gcpdiag-mocked and verify that the exit status is what we expect
	bin/gcpdiag-mocked lint --auth-adc --project=gcpdiag-gke1-aaaa; \
	  EXIT_CODE=$$?; \
	  if [ $$EXIT_CODE != 2 ]; then echo "incorrect exit code $$EXIT_CODE" >&2; exit 1; fi; \
	  exit 0

snapshots:
	pytest --snapshot-update --forked

gke-eol-file:
	./gcpdiag/lint/gke/eol_parser.sh > gcpdiag/lint/gke/eol.yaml

version:
	@echo $(VERSION)

build:
	rm -f dist/gcpdiag
	pyinstaller --workpath=.pyinstaller.build pyinstaller.spec

bump-version:
	bumpversion --commit minor

tarfile:
	# TODO: replace with something based on setuptools?
	rm -rf dist-tmp
	mkdir -p dist-tmp/$(DIST_NAME)/bin
	cp Pipfile Pipfile.lock README.md dist-tmp/$(DIST_NAME)
	cp bin/gcpdiag dist-tmp/$(DIST_NAME)/bin
	chmod +x dist-tmp/$(DIST_NAME)/bin/gcpdiag
	cp --parents gcpdiag/queries/client_secrets.json dist-tmp/$(DIST_NAME)
	find gcpdiag -name '*.py' -exec cp --parents '{}' dist-tmp/$(DIST_NAME) ';'
	chmod -R a+rX dist-tmp
	mkdir -p dist
	tar -C dist-tmp -czf dist/gcpdiag-$(VERSION).tar.gz --owner=0 --group=0 gcpdiag-$(VERSION)
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

.PHONY: test coverage-report version build bump-version tarfile release
