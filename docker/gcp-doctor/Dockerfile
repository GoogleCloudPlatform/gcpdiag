FROM python:3.8-slim-buster

# Add pipenv.
RUN pip install pipenv

# Add an entrypoint to create a user in /etc/passwd and /etc/group.
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]

# Install gcp-doctor + dependencies.
COPY dist/Pipfile.lock /opt/gcp-doctor/Pipfile.lock
RUN cd /opt/gcp-doctor && env PIPENV_VENV_IN_PROJECT=1 pipenv install --ignore-pipfile
COPY dist /opt/gcp-doctor
