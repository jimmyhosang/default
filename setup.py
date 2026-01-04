"""
Setup script for packaging Unified AI System as a macOS app bundle.

Usage:
    python setup.py py2app
    
The resulting app will be in dist/Unified AI System.app
"""
from setuptools import setup

APP = ['src/interface/desktop/app.py']
DATA_FILES = [
    ('web', ['src/interface/web/dist']),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,  # Add 'assets/icon.icns' when available
    'plist': {
        'CFBundleName': 'Unified AI System',
        'CFBundleDisplayName': 'Unified AI System',
        'CFBundleIdentifier': 'com.unifiedai.system',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,  # Set to True for menu-bar-only app
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
    },
    'packages': [
        'src',
        'uvicorn',
        'fastapi',
        'webview',
        'pystray',
        'PIL',
        'lancedb',
        'spacy',
        'sentence_transformers',
    ],
    'includes': [
        'src.interface.dashboard.server',
        'src.interface.desktop.tray',
        'src.interface.desktop.autostart',
        'src.store.semantic_store',
        'src.thought.rag',
    ],
    'excludes': [
        'matplotlib',
        'tkinter',
        'PyQt5',
        'PySide2',
    ],
}

setup(
    name='Unified AI System',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
