PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
BUILD1_CONFIG            := $(shell terraform output -raw build1_config)
BUILD2_CONFIG            := $(shell terraform output -raw build2_config)
BUILD3_CONFIG            := $(shell terraform output -raw build3_config)
BUCKET_WITH_RETENTION    := $(shell terraform output -raw bucket_with_retention)
ARTIFACT_REGISTRY        := $(shell terraform output -raw artifact_registry)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1
REGION_2     = europe-west1

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340005
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/cloudbuild.json \
	json-dumps/cloudbuild-$(REGION_1).json \
	json-dumps/cloudbuild-empty.json \
	json-dumps/bucket.json \
	json-dumps/artifact-registry-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/project.json \
	json-dumps/services.json

run-builds:
	gcloud builds submit --no-source --config $(BUILD1_CONFIG) \
		--project $(PROJECT_ID) || true
	gcloud builds submit --no-source --config $(BUILD2_CONFIG) \
		--project $(PROJECT_ID) || true
	gcloud builds submit --no-source --config $(BUILD3_CONFIG) \
		--project $(PROJECT_ID) || true

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudbuild.json:
	$(CURL) -fsS \
	  'https://cloudbuild.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/builds' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudbuild-$(REGION_1).json:
	$(CURL) -fsS \
	  'https://cloudbuild.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/builds' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudbuild-empty.json:
	$(CURL) -fsS \
	  'https://cloudbuild.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_2)/builds' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/bucket.json:
	$(CURL) -fv \
		'https://storage.googleapis.com/storage/v1/b/${BUCKET_WITH_RETENTION}' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/artifact-registry-policy.json:
	$(CURL) -fv \
		'https://artifactregistry.googleapis.com/v1/$(ARTIFACT_REGISTRY):getIamPolicy' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
		| $(SED_SUBST_FAKE) >$@
