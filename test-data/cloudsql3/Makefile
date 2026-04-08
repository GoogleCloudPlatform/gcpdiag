PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340006
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/services.json \
	json-dumps/project.json \
	json-dumps/cloudsql-instances.json

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/project.json:
	$(CURL) -fsS \
	  'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/cloudsql-instances.json:
	$(CURL) -fsS \
	  'https://sqladmin.googleapis.com/v1/projects/$(PROJECT_ID)/instances' \
	  | $(SED_SUBST_FAKE) >$@
