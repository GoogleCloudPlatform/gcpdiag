# Remote Container

[Remote Container](https://code.visualstudio.com/docs/remote/containers) (aka Development Container)
enables development fully inside a container, which allows for reproducible environments.
Besides allowing for an easier getting started experience, the environment can be rebuild with
`git reset --hard` and a container rebuild.

## Setup

### Requirements

Install the requirements on a Linux host:

1. Install podman on the machine with `apt-get install podman -y`
    1. Ensure you follow all the instructions for correct setup of podman on Debian-like distros.
    Please consult any public (or internal) documentation for the setup
2. Link podman as docker executable to avoid any overseen issues `ln -s /usr/bin/podman /usr/bin/docker`
3. Clone the repository in a folder of your choice on your host

### Open on a Workstation

To open the project in a remote container please follow the official
[documentation](https://code.visualstudio.com/docs/remote/containers#_open-an-existing-workspace-in-a-container)
or the short-listed steps:

1. Ensure you have [VS Code](https://code.visualstudio.com/) installed
2. Ensure the [Remote - Container](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
    extension is installed in VS Code
3. Open the source code folder in VS Code and click the pop-up "Reopen in Container"
    - If the pop-up does not show up by default, please consult the
    [documentation](https://code.visualstudio.com/docs/remote/containers#_open-an-existing-workspace-in-a-container)

### Open on a Remote Instance via SSH

The advantage of development via SSH (especially from non-Linux workstations) are a local UI renderer (VS Code),
without having to rely on graphical remoting protocols such as Chrome Remote Desktop.
Additionally, it gives the power of any possible instance and still has a local UX even though the code execution happens in the Cloud.

For more details please consult the
[documentation](https://code.visualstudio.com/remote/advancedcontainers/develop-remote-host#_connect-using-the-remote-ssh-extension-recommended)
or the following short-listed steps:

1. Ensure you have [VS Code](https://code.visualstudio.com/) installed locally
2. Ensure the [Remote - Container](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) &
    [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)
    extensions are installed in VS Code
3. Connect to the remote machine via SSH following the
    [documentation](https://code.visualstudio.com/remote/advancedcontainers/develop-remote-host#_connect-using-the-remote-ssh-extension-recommended)
4. Open the container on the remote similar to a local [workstation setup](#open-on-a-workstation)
   - If any issue occurs please consult the
      [documentation](https://code.visualstudio.com/remote/advancedcontainers/develop-remote-host)

The `git push` operation will need to be executed over SSH connection on the host (not in the container).

## Known Issues

- On the first start it might happen that VS Code does not correctly pick up the `pipenv` venv
  - As a workaround, restarting the container might help. Otherwise, please follow the
    [documentation](https://code.visualstudio.com/remote/advancedcontainers/develop-remote-host#_connect-using-the-remote-ssh-extension-recommended)
    to manually select an interpreter

- On the first start it might happen that VS Code does not correctly source the `pipenv` venv for new terminals
  - As a workaround, restarting the container might help.
    Otherwise, please execute `pipenv shell` manually

## Limitations

- `git commit` needs to be run in the container to allow correct execution of git hooks
- `git push` needs to be run on the host for authentication (especially in Google internal environments)

## Possible future improvements

- [ ] Install a Python linter (i.e. pylint) in the container to enable it by default for all developers
- [ ] Install a Python formatter in the container to enable it by default for all developers
