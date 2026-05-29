# utils/config_loader.py
import json
import os
from pathlib import Path

class JSONSettings:
    """
    A pure-Python replacement for QSettings that uses a JSON file.
    Maintains a similar API (value, setValue) for compatibility.
    """
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.data = {}
        self.load()

    def load(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.data = {}

    def save(self):
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def value(self, key, default=None):
        val = self.data.get(key, default)
        
        # If we stored a hex-encoded QByteArray, convert it back IF PySide6 is present
        if isinstance(val, str) and val.startswith("hex!!"):
            try:
                import sys
                if 'PySide6.QtCore' in sys.modules:
                    from PySide6.QtCore import QByteArray
                    return QByteArray.fromHex(val[5:].encode())
            except Exception:
                pass
        return val

    def setValue(self, key, value):
        # Handle QByteArray and other Qt objects without importing PySide6
        if hasattr(value, 'toHex'):
            try:
                # Convert QByteArray to a hex string for JSON safety
                value = f"hex!!{value.toHex().data().decode()}"
            except Exception:
                pass
        self.data[key] = value
        self.save()

    def sync(self):
        """Compatibility alias for QSettings.sync()"""
        self.save()

    def contains(self, key):
        return key in self.data

    def remove(self, key):
        if key in self.data:
            del self.data[key]
            self.save()

    def allKeys(self):
        return list(self.data.keys())
