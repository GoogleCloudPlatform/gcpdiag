## 2024-02-14 - Insecure Kubeconfig Permissions
**Vulnerability:** The temporary kubeconfig file `gcpdiag-config` containing credentials was created with default umask permissions (often 0644), making it readable by other users on the system.
**Learning:** `open(..., 'w')` respects the current umask, which is often not restrictive enough for sensitive files. `os.open` with `O_CREAT` only applies the mode if the file is being created; it ignores the mode if the file exists.
**Prevention:** Use `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` and wrap it with `os.fdopen`. Critically, ensure the file is removed if it already exists to guarantee the new permissions are applied, preventing race conditions where permissions remain insecure.
