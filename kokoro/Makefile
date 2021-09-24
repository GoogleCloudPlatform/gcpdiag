### Kokoro-specific (do not run interactively) ###

VERSION=$(shell sed -n 's/^current_version\s*=\s*//p' <../.bumpversion.cfg)

kokoro-build:
	make -C .. build
	# create the directory structure that we want in x20
	mkdir -p ../dist/x20/v$(VERSION)
	mv ../dist/gcpdiag ../dist/x20/v$(VERSION)
	ln -s v$(VERSION) ../dist/x20/latest
