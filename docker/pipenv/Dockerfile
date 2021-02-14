FROM python:3.8-slim-buster

# Add pipenv.
RUN pip install pipenv

# Debian packages.
RUN apt-get update && \
    apt-get -y install \
        bash \
        curl \
        git \
        make

# terraform
RUN curl https://releases.hashicorp.com/terraform/0.14.6/terraform_0.14.6_linux_amd64.zip | \
    gunzip - >/usr/bin/terraform && \
    chmod +x /usr/bin/terraform

# Add an entrypoint to create a user in /etc/passwd and /etc/group.
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
