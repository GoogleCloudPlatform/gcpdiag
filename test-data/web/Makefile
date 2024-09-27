CURL         =  exec curl

all:	\
	static/cloud-google-com-kubernetes-engine-docs-release-schedule \
	static/cloud-google-com-data-fusion-docs-support-version-support-policy \
	static/cloud-google-com-data-fusion-docs-concepts-configure-clusters

static/cloud-google-com-data-fusion-docs-concepts-configure-clusters-test:
	$(CURL) -fsS \
		'https://cloud.google.com/data-fusion/docs/concepts/configure-clusters' \
		--header "Content-Type:text/html" > $@

static/cloud-google-com-data-fusion-docs-support-version-support-policy-test:
	$(CURL) -fsS \
		'https://cloud.google.com/data-fusion/docs/support/version-support-policy' \
		--header "Content-Type:text/html" > $@

static/cloud-google-com-kubernetes-engine-docs-release-schedule-test:
	$(CURL) -fsS \
		'https://cloud.google.com/kubernetes-engine/docs/release-schedule' \
		--header "Content-Type:text/html" > $@
