"""
Setup script for packaging Unified AI System as a macOS app bundle.

Usage:
    python setup.py py2app
    
The resulting app will be in dist/Unified AI System.app
"""
import sys
sys.setrecursionlimit(5000)
from setuptools import setup, find_packages

APP = ['src/interface/desktop/app.py']
DATA_FILES = [
    ('web', ['src/interface/web/dist']),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'Unified AI System',
        'CFBundleDisplayName': 'Unified AI System',
        'CFBundleIdentifier': 'com.unifiedai.system',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,
        'NSRequiresAquaSystemAppearance': False,
    },
    'packages': find_packages(include=['src*']) + [
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
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
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
