## 2024-03-24 - Insecure Temporary File Creation in kubectl module

**Vulnerability:** The `KubectlExecutor.make_kube_config` function created a sensitive kubeconfig file (containing cluster credentials) in the user's cache directory with default file permissions (often 0644).
**Learning:** Python's standard `open()` function respects the current umask, which typically allows group/other read access. When handling sensitive files (credentials, keys), default permissions are insufficient.
**Prevention:** Use `os.open` with `os.O_CREAT | os.O_WRONLY | os.O_TRUNC` and explicit `0o600` mode to strictly limit permissions at creation time. Additionally, use `os.chmod(path, 0o600)` to safeguard against existing files with loose permissions being overwritten without permission updates.
