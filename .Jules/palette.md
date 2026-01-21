## 2024-05-23 - [CLI Output Coloring]
**Learning:** For CLI tools like `gcpdiag` using `blessings` for terminal output, visual hierarchy can be significantly improved by coloring summary statistics and status indicators. Overriding `BaseOutput` methods in `TerminalOutput` allows for targeted visual enhancements without affecting other output formats (JSON/CSV).
**Action:** When adding visual improvements to CLI output, ensure consistency in color usage (Green=OK, Red=Fail, Yellow=Skip/Warn) and verify with a mock terminal environment since `blessings` detects TTY.
