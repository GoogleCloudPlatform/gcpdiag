## Introduction

We use the following tools in this project:

-   Gerrit: Google internal code review
-   Kokoro: Google internal CI/CD
-   pipenv: Manage Python virtual environments
-   [pre-commit](https://pre-commit.com): Manage git presubmit hooks (we also
    use this as presubmit check.
-   pytest: Testing framework
-   yapf: Code formatting

## Development setup

-   Install `pipenv`

    ```
    apt install pipenv`
    ```

-   Start a shell with pipenv and run pre-commit install the pre-commit hooks:

    ```
    pipenv shell
    pre-commit install
    ```
