## 2024-02-14 - [Insecure Temporary File Creation]
**Vulnerability:** The `gcpdiag` tool was creating a temporary `kubeconfig` file containing sensitive credentials in the user's cache directory with default permissions (often `0664`), making it readable by other users on the system.
**Learning:** Python's default `open(path, 'w')` respects the system `umask`, which is often lenient (e.g., `0002`). This is dangerous for files containing secrets.
**Prevention:** Always use `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` followed by `os.fdopen` when creating files that will contain sensitive information. Explicitly restricting permissions is safer than relying on defaults.
