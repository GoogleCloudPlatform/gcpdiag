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

spelling:
	 pip install -U PyEnchant; pylint --disable all --enable spelling --spelling-dict en_US gcpdiag

snapshots:
	pytest --snapshot-update --forked -v -v

gke-eol-file:
	./gcpdiag/lint/gke/eol_parser.sh > gcpdiag/lint/gke/eol.yaml

version:
	@echo $(VERSION)

build:
	rm -f dist/gcpdiag
	pyinstaller --workpath=.pyinstaller.build pyinstaller.spec

bump-version:
	bumpversion --commit minor

new-rule:
	python cookiecutter-gcpdiag-rule/cookiecutter_runner.py

tarfile:
	# TODO: replace with something based on setuptools?
	rm -rf dist-tmp
	mkdir -p dist-tmp/$(DIST_NAME)/bin
	cp Pipfile Pipfile.lock README.md dist-tmp/$(DIST_NAME)
	cp bin/gcpdiag dist-tmp/$(DIST_NAME)/bin
	chmod +x dist-tmp/$(DIST_NAME)/bin/gcpdiag
	cp --parents gcpdiag/queries/client_secrets.json dist-tmp/$(DIST_NAME)
	find gcpdiag -name '*.py' -exec cp --parents '{}' dist-tmp/$(DIST_NAME) ';'
	find gcpdiag -name '*.jinja' -exec cp --parents '{}' dist-tmp/$(DIST_NAME) ';'
	find gcpdiag -name 'gcpdiag/runbook/gce/disk_performance_benchmark/*.json' -exec cp --parents '{}' dist-tmp/$(DIST_NAME) ';'
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
	# Push to the release branch and tag the release.
	# Note: We want ff-only because otherwise the commit ids will be different
	# between master and release, and that causes problems with tags
	# (and in particular the version tag pointing to a commit in the release
	# branch, so that git describe doesn't work correctly in master, which
	# itself disrupts the creation of tags in GitHub by Copybara),
	# If this fails, you probably should force-push from master to the
	# release branch. The release branch is only used to kick off releases
	# in Kokoro.
	git merge --ff-only origin/release
	git push origin HEAD:release
	git push --tags
	# increment the version (and add back '-test')
	bumpversion --commit minor
	git push origin HEAD:refs/for/master

runbook-docs:
  # Help developers generate and update docs before actually running full precommit
	pre-commit run gcpdiag-custom-runbook-rule

runbook-starter-code:
	@[ "$(name)" ] || (echo "name is not set. Usage: make $@ name=product/runbook-id" && false)
	@PYTHON=`which python3 || which python`;\
	if [ -z "$$PYTHON" ]; then \
		echo "Python is not installed or not found in PATH"; \
		exit 1; \
	fi;\
	echo "Using Python at $$PYTHON"; \
	$$PYTHON bin/runbook-starter-code-generator py_path=$$PYTHON name=$(name) prepenv=$(prepenv)

.PHONY: test coverage-report version build bump-version tarfile release runbook-docs runbook-starter-code spelling
