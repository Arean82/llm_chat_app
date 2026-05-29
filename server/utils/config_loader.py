# utils/config_loader.py
import json
import os
from pathlib import Path

import configparser
import os
from pathlib import Path

class INISettings:
    """
    A pure-Python replacement for QSettings that uses an INI file.
    Maintains a similar API (value, setValue) for compatibility across headless and GUI environments.
    """
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.parser = configparser.ConfigParser()
        self.parser.optionxform = str  # Preserve case sensitivity
        self.load()

    def load(self):
        if self.file_path.exists():
            try:
                self.parser.read(self.file_path, encoding='utf-8')
            except Exception as e:
                print(f"Error loading settings: {e}")
        if not self.parser.has_section("General"):
            self.parser.add_section("General")

    def save(self):
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def value(self, key, default=None):
        if not self.parser.has_option("General", key):
            return default
            
        val = self.parser.get("General", key)
        
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
                # Convert QByteArray to a hex string for safe INI storage
                value = f"hex!!{value.toHex().data().decode()}"
            except Exception:
                pass
        
        if not self.parser.has_section("General"):
            self.parser.add_section("General")
            
        self.parser.set("General", key, str(value))
        self.save()

    def sync(self):
        """Compatibility alias for QSettings.sync()"""
        self.save()

    def contains(self, key):
        return self.parser.has_option("General", key)

    def remove(self, key):
        if self.parser.has_option("General", key):
            self.parser.remove_option("General", key)
            self.save()

    def allKeys(self):
        if self.parser.has_section("General"):
            return self.parser.options("General")
        return []
