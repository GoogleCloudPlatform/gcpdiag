PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

TOPIC := $(shell terraform output -raw topic)
SUBSCRIPTION := $(shell terraform output -raw subscription)

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340009
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/topics.json \
	json-dumps/topic-iam.json \
	json-dumps/subscriptions.json \
	json-dumps/subscriptions-iam.json

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/topics.json:
	$(CURL) -fv \
		'https://pubsub.googleapis.com/v1/projects/${PROJECT_ID}/topics' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/topic-iam.json:
	$(CURL) -fv \
		'https://pubsub.googleapis.com/v1/projects/$(PROJECT_ID)/topics/$(TOPIC):getIamPolicy' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/subscriptions.json:
	$(CURL) -fv \
		'https://pubsub.googleapis.com/v1/projects/${PROJECT_ID}/subscriptions' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/subscriptions-iam.json:
	$(CURL) -fv \
		'https://pubsub.googleapis.com/v1/projects/$(PROJECT_ID)/subscriptions/$(SUBSCRIPTION):getIamPolicy' \
		| $(SED_SUBST_FAKE) >$@
