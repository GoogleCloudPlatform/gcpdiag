---
title: "Development Environment"
linkTitle: "Dev Environment"
weight: 1
description: >
  How to prepare your environment to do development work.
---

## Environment setup

-   Make a fork of the official gcpdiag repository

-   Clone your fork

    ```
    git clone git@github.com:xxxxxx/gcpdiag.git
    cd gcpdiag
    git submodule update --init
    ```


-   Install pipenv and all the required Python dependencies:

    ```
    apt install pipenv
    pipenv shell
    pipenv install --dev
    ```

    or for mac:

    ```
    brew install pipenv
    pipenv shell
    pipenv install --dev
    ```

-   Install pre-commit (for the "presubmit" tests):

    ```
    pipenv shell
    pre-commit install
    ```

-   You can run tests and gcpdiag in the pipenv shell, so that all required
    modules are installed:

    ```
    pipenv shell
    make test
    bin/gcpdiag lint --project=xxx
    ```
