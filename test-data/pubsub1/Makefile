PROJECT_ID := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_ID_SUFFIX := $(shell terraform output -json project_id_suffix)
PROJECT_NR  := $(shell terraform output -json project_nr | sed -e 's|"||g')
ORG_ID      := $(shell terraform output -json org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

TOPIC := $(shell terraformm output -json topic | sed -e 's|"||g')
SUBSCRIPTION := $(shell terraform output -json subscription | sed -e 's|"||g')
BQ_SUBSCRIPTION := $(shell terraform output -json bqsubscription | sed -e 's|"||g')
BUCKET_ID := $(shell terraform output -json gcs_subscription_bucket_name | sed -e 's|"||g')

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
	json-dumps/pull-subscription.json \
	json-dumps/subscriptions-iam.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/monitoring-query.json \
	json-dumps/bucket-roles.json

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

json-dumps/pull-subscription.json:
	$(CURL) -fv \
		'https://pubsub.googleapis.com/v1/projects/$(PROJECT_ID)/subscriptions/$(SUBSCRIPTION)' \
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


define BQ_SUB_PUSH_REQUESTS_QUERY
{ \
  "query": "fetch pubsub_subscription::pubsub.googleapis.com/subscription/push_request_count \
	| filter resource.project_id == '"'"'$(PROJECT_ID)'"'"' && resource.subscription_id == '"'"'$(BQ_SUBSCRIPTION)'"'"'\
  | within 10m \
  | group_by [metric.response_class],[value_push_request_count_aggregate: aggregate(value.push_request_count)] \
	| within 10m \
  " \
}
endef
json-dumps/monitoring-query.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query'\
		--header "Content-Type: application/json" -X POST \
		--data '$(BQ_SUB_PUSH_REQUESTS_QUERY)' \
		| $(SED_SUBST_FAKE) >$@


json-dumps/bucket-roles.json:
	$(CURL) -fv \
		'https://storage.googleapis.com/storage/v1/b/${BUCKET_ID}/iam' \
		| $(SED_SUBST_FAKE) >$@
