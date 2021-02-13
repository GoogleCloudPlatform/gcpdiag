VERSION=0.1

test:
	coverage run --include='gcp_doctor/*' -m pytest

coverage-report:
	coverage report -m

version:
	@echo $(VERSION)

dist:
	rm -rf dist-tmp
	mkdir -p dist-tmp/gcp-doctor-$(VERSION)
	cp Pipfile Pipfile.lock README.md dist-tmp/gcp-doctor-$(VERSION)
	mkdir dist-tmp/gcp-doctor-$(VERSION)/bin
	cp bin/gcp-doctor dist-tmp/gcp-doctor-$(VERSION)/bin
	cp -a gcp_doctor dist-tmp/gcp-doctor-$(VERSION)/gcp_doctor
	sed -i -e "s/^VERSION =.*/VERSION = '$(VERSION)'/" dist-tmp/gcp-doctor-$(VERSION)/gcp_doctor/config.py
	chmod -R a+rX dist-tmp
	tar -C dist-tmp -czf gcp-doctor-$(VERSION).tar.gz --owner=0 --group=0 gcp-doctor-$(VERSION)
	rm -rf dist-tmp

.PHONY: test coverage-report dist
