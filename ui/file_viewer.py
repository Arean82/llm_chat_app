# ui/file_viewer.py
# This module defines a reusable dialog for displaying text files (Markdown or Plain Text) with support for external images. It uses a custom QTextBrowser to handle image loading. 
# The BadgeCacheWorker runs in a background thread to download badge images and update the HTML content without freezing the UI.    

import re
import urllib.request
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton
from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QDesktopServices
from pathlib import Path

from utils.path_utils import get_resource_path, get_cache_path

class BadgeCacheWorker(QThread):
    """Background thread to download badge images so the UI doesn't freeze"""
    finished = Signal(str) 

    def __init__(self, html_content: str):
        super().__init__()
        self.html_content = html_content

    def run(self):
        # Robust regex that finds src="url" NO MATTER the order of attributes
        pattern = r'(<img\s[^>]*?)src="(https?://[^"]+)"'
        cache_dir = get_resource_path("resources/badge_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        def download_and_replace(match):
            full_tag_start = match.group(1)
            url = match.group(2)
            
            filename = url.split("/")[-1]
            # Handle URLs with query parameters
            if '?' in filename:
                filename = filename.split('?')[0]
                
            if not filename.endswith('.svg') and not filename.endswith('.png'):
                filename += '.svg'
                
            local_path = cache_dir / filename
            
            if not local_path.exists():
                try:
                    # Add User-Agent for shields.io
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    # 5-second timeout
                    with urllib.request.urlopen(req, timeout=5) as response:
                        with open(local_path, 'wb') as f:
                            f.write(response.read())
                except Exception as e:
                    return match.group(0)  # Keep original URL if download fails
            
            local_url = QUrl.fromLocalFile(str(local_path.absolute())).toString()
            return f'{full_tag_start}src="{local_url}"'

        updated_html = re.sub(pattern, download_and_replace, self.html_content)
        self.finished.emit(updated_html)

class FileViewerDialog(QDialog):
    """Reusable dialog to display text files (Markdown or Plain Text)"""
    
    def __init__(self, title: str, file_names: list, is_markdown: bool = False, size: tuple = (600, 450), parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(size[0], size[1])  
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.anchorClicked.connect(self.on_anchor_clicked)
        
        self.load_file(file_names, is_markdown)
        layout.addWidget(self.text_browser)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def on_anchor_clicked(self, url):
        """Handle internal anchor links and external URLs"""
        url_str = url.toString()
        if url_str.startswith("#"):
            # Internal anchor - scroll to anchor
            self.text_browser.scrollToAnchor(url_str[1:])
        else:
            # External link - open in default browser
            QDesktopServices.openUrl(url)
    
    def load_file(self, possible_names: list, is_markdown: bool):
        base_dir = Path(__file__).parent.parent
        content = f"<i>File not found. Searched for: {', '.join(possible_names)}</i>"
        
        for name in possible_names:
            path = base_dir / name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    break
                except Exception:
                    content = f"<i>Error reading file: {name}</i>"
                    
        if is_markdown:
            self.text_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #FFFFFF;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    padding: 15px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                }
            """)
            import markdown
            
            # Convert MD to HTML
            html = markdown.markdown(content, extensions=['extra', 'fenced_code', 'codehilite'])
            
            # Inject CSS to preserve newlines in code blocks
            style_fix = """
            <style>
                pre { white-space: pre-wrap; font-family: 'Consolas', 'Courier New', monospace; background-color: #f6f8fa; padding: 10px; border-radius: 4px; }
                code { white-space: pre-wrap; font-family: 'Consolas', 'Courier New', monospace; }
            </style>
            """
            
            # Prepend the style to the HTML
            html = style_fix + html

            # Show text immediately
            self.text_browser.setHtml(html)
            
            # Start background thread to download badges
            self.cache_worker = BadgeCacheWorker(html)
            self.cache_worker.finished.connect(self.on_badges_cached)
            self.cache_worker.start()
            
        else:
            self.text_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #F5F5F5;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    padding: 15px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 12px;
                }
            """)
            self.text_browser.setPlainText(content)

    def on_badges_cached(self, updated_html: str):
        """Slot called by the background thread when downloads are complete"""
        # Preserve scroll position
        scroll_pos = self.text_browser.verticalScrollBar().value()
        
        # Inject the HTML with the local image paths
        self.text_browser.setHtml(updated_html)
        
        # Restore scroll position
        self.text_browser.verticalScrollBar().setValue(scroll_pos)