## 2024-05-23 - [Insecure File Permissions]
**Vulnerability:** The `gcpdiag-config` file containing sensitive Kubernetes credentials was created with default file permissions (e.g., 644), making it readable by other users on the system.
**Learning:** Even temporary configuration files stored in cache directories must be treated as sensitive if they contain credentials. Standard `open()` does not provide sufficient control over permissions for sensitive files.
**Prevention:** Use `os.open` with `O_CREAT | O_WRONLY | O_TRUNC` and mode `0o600` for creating sensitive files. Also, ensure to update permissions (e.g., `os.chmod`) if the file might already exist.
