# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['bin/gcpdiag'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['pyinstaller'],
             runtime_hooks=[],
             excludes=['django'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# add runbook templates as data
for root, dirs, files in os.walk("gcpdiag/runbook"):
  for f in files:
    if f.endswith("jinja"):
      path = os.path.join(root, f)
      a.datas.append((path, path, 'DATA'))

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='gcpdiag',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
