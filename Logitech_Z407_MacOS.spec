# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('assets', 'assets'), ('static', 'static')],
    hiddenimports=['pyscreeze', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Logitech Z407 Remote Control',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Logitech Z407 Remote Control',
)
app = BUNDLE(
    coll,
    name='Logitech Z407 Remote Control.app',
    icon='assets/icon_app.icns',
    bundle_identifier='com.lcy000.logitech-z407-remote-control',
    info_plist={
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '0.1.0',
        'LSUIElement': True,
        'NSBluetoothAlwaysUsageDescription': 'This app uses Bluetooth to find and control your Logitech Z407 speaker.',
        'NSBluetoothPeripheralUsageDescription': 'This app uses Bluetooth to find and control your Logitech Z407 speaker.',
    },
)
