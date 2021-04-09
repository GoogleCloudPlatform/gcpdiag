"""pyinstaller configuration for gcp_doctor.lint."""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = \
  collect_submodules('gcp_doctor.lint.gce') + \
  collect_submodules('gcp_doctor.lint.gke')
