# Test data

Many of the tests in gcpdiag are implemented using real API responses that
are fetched with curl and stored in this directory. The API is then mocked
and returns data from the response files (in JSON format).

In order to create the response data, we use real GCP projects. We setup
everything using Terraform, and fetch the responses with curl. We create
ephemeral projects only for the purprose of generating those API responses,
and delete the projects afterwards.

Every directory has a different project template, based on the test use
case.

In order to run terraform, you will need to supply the organization id and
billing account id as variables:

```
$ export TF_VAR_billing_account_id=0123456-ABCDEF-987654
$ export TF_VAR_org_id=123456789012
$ cd projectdir
$ terraform init
$ terraform apply
```

The API responses are generated using curl commands started with make:

```
$ make all
```

### Creating new projects

If you need to create a project template for a new use case, proceed as follows:

1. Create a new directory

1. Copy the following files as starting point:

   - gce1/Makefile
   - gce1/project.tf

1. Create a Makefile file that looks as follows:

   ```
   PROJECT_ID  := $(shell terraform output -raw project_id)
   PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
   PROJECT_NR  := $(shell terraform output -raw project_nr)
   ORG_ID      := $(shell terraform output -raw org_id)
   CURL         = ../../bin/curl-wrap.sh
   JSON_CLEANER = ../../bin/json-cleaner

   FAKE_PROJECT_ID_SUFFIX = aaaa
   FAKE_PROJECT_NR = 12340001
   FAKE_ORG_ID = 11112222
   SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
   		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
   		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

   all:	\
   	json-dumps/project.json \
   	json-dumps/services.json

   json-dumps/project.json:
   	$(CURL) -fsS \
   		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
   		| $(SED_SUBST_FAKE) >$@

   json-dumps/services.json:
   	$(CURL) -fv \
   	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
   		| $(SED_SUBST_FAKE) >$@
   ```

1. Search and replace the following strings:

   - `gce1`: use your own short project template name.
   - `12340001`: this is the fake project number. Use a number that is not yet
     used in any other template (keep the same '123400' prefix).

1. Create .tf files with all the resources that you need.

1. Add curl calls to the Makefile for all json files that you need.
