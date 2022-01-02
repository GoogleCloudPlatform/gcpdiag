   PROJECT_ID  := $(shell terraform output -raw project_id)
   PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
   PROJECT_NR  := $(shell terraform output -raw project_nr)
   ORG_ID      := $(shell terraform output -raw org_id)
   CURL         = ../../bin/curl-wrap.sh
   JSON_CLEANER = ../../bin/json-cleaner
   BUCKET_ID = gcpdiag-gcs1bucket-aaaa

   FAKE_PROJECT_ID_SUFFIX = aaaa
   FAKE_PROJECT_NR = 12340008
   FAKE_ORG_ID = 11112222
   SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
   		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
   		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

   all:	\
   	json-dumps/project.json \
   	json-dumps/services.json \
		json-dumps/storage.json \
		json-dumps/bucket-roles.json

   json-dumps/project.json:
   	$(CURL) -fsS \
   		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
   		| $(SED_SUBST_FAKE) >$@

   json-dumps/services.json:
   	$(CURL) -fv \
   	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
   		| $(SED_SUBST_FAKE) >$@

   json-dumps/storage.json:
   	$(CURL) -fv \
   	        'https://storage.googleapis.com/storage/v1/b?project=$(PROJECT_ID)' \
   		| $(SED_SUBST_FAKE) >$@

   json-dumps/bucket-roles.json:
   	$(CURL) -fv \
   	        'https://storage.googleapis.com/storage/v1/b/${BUCKET_ID}/iam' \
   		| $(SED_SUBST_FAKE) >$@
