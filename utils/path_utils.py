# utils/path_utils.py
# This file contains utility functions for handling file paths in the LLM Chat App. It includes a function to get the absolute path to resources, which works both in development and when the app is packaged with PyInstaller.    

import sys
from pathlib import Path

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).parent.parent
    return base_path / relative_path