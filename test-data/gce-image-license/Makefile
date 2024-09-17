CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

CENTOS_CLOUD= centos-cloud
COS_CLOUD= cos-cloud
DEBIAN_CLOUD= debian-cloud
FEDORA_CLOUD= fedora-cloud
FEDORA_CORECOS_CLOUD= fedora-coreos-cloud
OPENSUSE_CLOUD= opensuse-cloud
RHEL_CLOUD= rhel-cloud
RHEL_SAP_CLOUD= rhel-sap-cloud
ROCKY_LINUX_CLOUD= rocky-linux-cloud
SUSE_CLOUD= suse-cloud
SUSE_SAP_CLOUD= suse-sap-cloud
UBUNTU_OS_CLOUD= ubuntu-os-cloud
UBUNTU_OS_PRO_CLOUD= ubuntu-os-pro-cloud
WINDOW_CLOUD= windows-cloud
WINDOWS_SQL_CLOUD= windows-sql-cloud

all:	\
	json-dumps/${CENTOS_CLOUD}-licenses.json \
	json-dumps/${COS_CLOUD}-licenses.json \
	json-dumps/${DEBIAN_CLOUD}-licenses.json \
	json-dumps/${FEDORA_CLOUD}-licenses.json \
	json-dumps/${FEDORA_CORECOS_CLOUD}-licenses.json \
	json-dumps/${OPENSUSE_CLOUD}-licenses.json \
	json-dumps/${RHEL_CLOUD}-licenses.json \
	json-dumps/${RHEL_SAP_CLOUD}-licenses.json \
	json-dumps/${ROCKY_LINUX_CLOUD}-licenses.json \
	json-dumps/${SUSE_CLOUD}-licenses.json \
	json-dumps/${SUSE_SAP_CLOUD}-licenses.json \
	json-dumps/${UBUNTU_OS_CLOUD}-licenses.json \
	json-dumps/${UBUNTU_OS_PRO_CLOUD}-licenses.json \
	json-dumps/${WINDOW_CLOUD}-licenses.json \
	json-dumps/${WINDOWS_SQL_CLOUD}-licenses.json

json-dumps/%-licenses.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$*/global/licenses' \
		--header "Content-Type:text/json" > $@
