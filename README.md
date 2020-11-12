## Introduction

Important links:

-   **Mail group**: [go/gcp-doctor-team](http://go/gcp-doctor-team)
-   **Chat room**:
    [go/gcp-doctor-chat](https://mail.google.com/mail/u/0/chat/#chat/space/AAAAN1xhYE0)
-   **Git repo**: [go/gcp-doctor-git](http://go/gcp-doctor-git)
-   **Gerrit code review**: [go/gcp-doctor-review](http://go/gcp-doctor-review)
-   **Kokoro jobs**: [go/gcp-doctor-kokoro](http://go/gcp-doctor-kokoro)
-   **Documents**:
    -   [Proposal](http://gcp-doctor-proposal)
    -   [Design doc](http://gcp-doctor-design) (architecture, etc., must read!)

We use the following tools in this project:

-   Gerrit: Google internal code review
-   Kokoro: Google internal CI/CD for code outside of Google3
-   pipenv: Manage Python virtual environments
-   [pre-commit](https://pre-commit.com): Manage git presubmit hooks (we also
    use this as presubmit check in Kokoro).
-   pytest: Testing framework
-   yapf: Code formatting
-   docker: test running environment (for Kokoro jobs)
-   terraform: Test projects setup ("dummies" used in testing)

## Development setup

-   Install the required Gerrit commit hook:

    ```
    f=$(git rev-parse --git-dir)/hooks/commit-msg
    mkdir -p $(dirname $f)
    curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg
    chmod +x $f
    ```

-   Install `terraform` or install Docker and put the `bin` directory in this
    repository in your PATH (there is a docker-based terraform wrapper).

-   Install `pipenv`

    ```
    apt install pipenv`
    ```

-   Start a shell with pipenv and run pre-commit install the pre-commit hooks:

    ```
    pipenv shell
    pre-commit install
    ```

-   You can run tests and gcp-doctor in the pipenv shell, so that all required
    modules are installed:

    ```
    pipenv shell
    pytest
    bin/gcp-doctor
    ```

## Code Review and Automated Testing

We use Gerrit + Kokoro to implement a code review process and automated testing
of all code before it is merged.

[Gerrit](go/gerrit) models the same workflow as CLs in Piper, but using git.
This is a bit different than git pull requests, because the code is pushed to
the same central repository under a special reference (sort of a branch), and
then merged when the code review process is completed. Doing the Gerrit
[codelab](https://g3doc.corp.google.com/company/teams/gerritcodereview/users/intro-codelab.md)
is recommended.
