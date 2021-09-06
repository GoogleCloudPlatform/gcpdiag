### Kokoro-specific (do not run interactively) ###

kokoro-build:
	make -C .. build
	# create the directory structure that we want in x20
	mkdir -p ../dist/x20/v$(VERSION)
	mv ../dist/gcp-doctor dist/x20/v$(VERSION)
	ln -s v$(VERSION) ../dist/x20/latest
	# make sure that the files are not group-writable, because
	# otherwise all mdb/gcp-doctor-users would be allowed, and this
	# is not permitted (more than 500 users)
	chmod -R go-w ../dist/x20
