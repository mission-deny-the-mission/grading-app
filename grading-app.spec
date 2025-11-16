# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Grading App Desktop Application

This spec file configures PyInstaller to bundle the Flask web application
into a standalone desktop executable for Windows, macOS, and Linux.

Entry Point: desktop/main.py
Build Command: pyinstaller grading-app.spec
Output: dist/GradingApp/

For more information, see desktop/README.md
"""

# Hidden imports required for runtime module loading
# These modules are imported dynamically by SQLAlchemy and Flask
hiddenimports = [
    # SQLAlchemy runtime imports
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.postgresql',  # For compatibility/migration

    # Flask extensions
    'flask_sqlalchemy',
    'flask_migrate',

    # Desktop app dependencies
    'apscheduler',
    'apscheduler.schedulers',
    'apscheduler.schedulers.background',

    # Additional runtime dependencies
    'werkzeug.security',
    'jinja2',
]

# Analyze the application and collect all dependencies
a = Analysis(
    ['desktop/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),  # Flask HTML templates
        ('static', 'static'),        # Static assets (CSS, JS, images)
        # Note: uploads/ directory is NOT included - user data stays separate
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Create Python bytecode archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Use COLLECT mode for faster startup
    name='GradingApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable with UPX (if available)
    console=False,  # No console window on startup (GUI mode)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect all files into distribution directory
# This uses --onedir mode (not --onefile) for faster startup
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GradingApp',
)

# Platform-specific configurations can be added here
# For macOS bundle (.app):
# app = BUNDLE(
#     coll,
#     name='GradingApp.app',
#     icon='desktop/resources/icon.icns',
#     bundle_identifier='com.yourorg.gradingapp',
# )
