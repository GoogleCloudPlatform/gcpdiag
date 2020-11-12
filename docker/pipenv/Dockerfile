FROM mirror.gcr.io/library/debian:stable-slim
# debian packages
RUN apt-get update && \
    apt-get -y install \
        bash \
        curl \
        git \
        make \
        python3 \
        python3-distutils

# terraform
RUN curl https://releases.hashicorp.com/terraform/0.13.5/terraform_0.13.5_linux_amd64.zip | \
    gunzip - >/usr/bin/terraform && \
    chmod +x /usr/bin/terraform

# pip / pipenv
# note: python3-pip brings in 400MB+, so we install it manually instead...
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
    python3 get-pip.py; \
    rm get-pip.py
RUN pip install pipenv

# add an entrypoint to create a user in /etc/passwd and /etc/group
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
