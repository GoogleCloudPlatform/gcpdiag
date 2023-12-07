PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
BILLING_ACCOUNT_ID := $(shell terraform output -raw billing_account_id)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340092
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		 -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		 -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:  \
  json-dumps/project.json \
  json-dumps/services.json \
  json-dumps/cost_insights.json \
  json-dumps/all_projects.json \
  json-dumps/all_billing_account_projects.json \
  json-dumps/billing_account.json \
  json-dumps/all_billing_accounts.json \
  json-dumps/project_billing_info.json

json-dumps/project.json:
	$(CURL) -fsS \
	  'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/cost_insights.json:
	$(CURL) -fv \
	-H "Authorization: Bearer $(gcloud auth print-access-token)" \
	-H "x-goog-user-project: $(PROJECT_ID)" \
	  'https://recommender.googleapis.com/v1/projects/$(PROJECT_ID)/locations/global/insightTypes/google.billing.CostInsight/insights' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/projects.json:
	$(CURL) -v \
	  'https://cloudresourcemanager.googleapis.com/v1/projects' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/all_billing_account_projects.json:
	$(CURL) -fv\
	  'https://cloudbilling.googleapis.com/v1/{billingAccounts/$(BILLING_ACCOUNT_ID)}/projects' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/billing_account.json:
	$(CURL) -fv \
	  'https://cloudbilling.googleapis.com/v1/{billingAccounts/$(BILLING_ACCOUNT_ID)}' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/all_billing_accounts.json:
	$(CURL) -v \
	  'https://cloudbilling.googleapis.com/v1/billingAccounts' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/project_billing_info.json:
	$(CURL) -fv \
	  'https://cloudbilling.googleapis.com/v1/{projects/$(PROJECT_ID)}/billingInfo' \
	  | $(SED_SUBST_FAKE) >$@
