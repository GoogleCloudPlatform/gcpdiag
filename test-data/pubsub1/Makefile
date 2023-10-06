#terraform config for gcpdiag
# To run the commands use: /google/data/ro/teams/terraform/bin/terraform
PROJECT_ID := $(shell /google/data/ro/teams/terraform/bin/terraform output project_id | sed -e 's|"||g')
PROJECT_ID_SUFFIX := $(shell /google/data/ro/teams/terraform/bin/terraform output -json project_id_suffix)
PROJECT_NR  := $(shell /google/data/ro/teams/terraform/bin/terraform output -json project_nr | sed -e 's|"||g')
ORG_ID      := $(shell /google/data/ro/teams/terraform/bin/terraform output -json org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

TOPIC := $(shell /google/data/ro/teams/terraform/bin/terraform output -json topic)
SUBSCRIPTION := $(shell /google/data/ro/teams/terraform/bin/terraform output -json subscription | sed -e 's|"||g')


FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340014
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
	json-dumps/subscriptions-iam.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json

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

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
		| $(SED_SUBST_FAKE) >$@
