# ui/file_viewer.py
# This module defines a reusable dialog for displaying text files (Markdown or Plain Text) with support for external images. It uses a custom QTextBrowser to handle image loading. 
# The BadgeCacheWorker runs in a background thread to download badge images and update the HTML content without freezing the UI.    

import re
import urllib.request
from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QDesktopServices, QTextCursor, QMouseEvent
from pathlib import Path

from utils.path_utils import get_resource_path, get_cache_path

class BadgeCacheWorker(QThread):
    """Background thread to download badge images so the UI doesn't freeze"""
    finished = Signal(str) 

    def __init__(self, html_content: str):
        super().__init__()
        self.html_content = html_content

    def run(self):
        pattern = r'(<img\s[^>]*?)src="(https?://[^"]+)"'
        cache_dir = get_resource_path("resources/badge_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        def download_and_replace(match):
            full_tag_start = match.group(1)
            url = match.group(2)
            
            filename = url.split("/")[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
                
            if not filename.endswith('.svg') and not filename.endswith('.png'):
                filename += '.svg'
                
            local_path = cache_dir / filename
            
            if not local_path.exists():
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        with open(local_path, 'wb') as f:
                            f.write(response.read())
                except Exception:
                    return match.group(0) 
            
            local_url = QUrl.fromLocalFile(str(local_path.absolute())).toString()
            return f'{full_tag_start}src="{local_url}"'

        updated_html = re.sub(pattern, download_and_replace, self.html_content)
        self.finished.emit(updated_html)

class MarkdownBrowser(QTextBrowser):
    """
    QTextBrowser that manually handles mouse clicks on links.
    This bypasses Qt's internal link resolution which fails for Markdown anchors.
    """
    def mousePressEvent(self, event: QMouseEvent):
        # 1. Check if the user clicked on a link
        link = self.anchorAt(event.pos())
        
        if link:
            url = QUrl(link)
            
            # 2. Handle Internal Anchors (#)
            # We check if there is a fragment (the part after #)
            if url.fragment():
                # Get the text of the anchor (e.g., "-features" from "#-features")
                anchor_text = url.fragment()
                # Normalize it by stripping dashes and spaces to match the header text
                anchor_clean = anchor_text.replace("-", "").replace("_", "").replace(" ", "").lower()
                
                if self._scroll_to_anchor(anchor_clean):
                    # If we successfully handled the scroll, accept the event 
                    # and stop Qt from trying to handle the link itself.
                    event.accept()
                    return

            # 3. Handle External Links (http/https)
            if url.scheme() in ('http', 'https'):
                QDesktopServices.openUrl(url)
                event.accept()
                return

        # If we didn't handle it (e.g., it was text, not a link), pass to parent
        super().mousePressEvent(event)

    def _scroll_to_anchor(self, anchor_clean: str) -> bool:
        """
        Fuzzy search the document for a header matching the anchor.
        """
        if not anchor_clean:
            return False

        doc = self.document()
        block = doc.begin()

        while block.isValid():
            text = block.text()
            # Normalize the block text for comparison
            text_clean = text.replace("-", "").replace("_", "").replace(" ", "").lower()
            
            # Check if the anchor string is contained in the block text
            # e.g. "prerequisites" matches "## Prerequisites"
            if anchor_clean in text_clean:
                # Found it. Move cursor and scroll.
                cursor = QTextCursor(block)
                self.setTextCursor(cursor)
                self.ensureCursorVisible()
                return True
            
            block = block.next()
            
        return False

class FileViewerDialog(QDialog):
    """Reusable dialog to display text files (Markdown or Plain Text)"""
    
    def __init__(self, title: str, file_names: list, is_markdown: bool = False, size: tuple = (600, 450), parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(size[0], size[1])  
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Use our custom MarkdownBrowser
        self.text_browser = MarkdownBrowser(self)
        
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
            # Note: We do not need to modify the HTML content manually anymore 
            # because our mousePressEvent uses fuzzy text matching instead of ID matching.
            html = markdown.markdown(content, extensions=['extra', 'fenced_code', 'codehilite'])
            
            # Inject CSS
            style_fix = """
            <style>
                pre { white-space: pre-wrap; font-family: 'Consolas', 'Courier New', monospace; background-color: #f6f8fa; padding: 10px; border-radius: 4px; }
                code { white-space: pre-wrap; font-family: 'Consolas', 'Courier New', monospace; }
                
                /* Make links look clickable */
                a { color: #0078d4; text-decoration: none; cursor: pointer; }
                a:hover { text-decoration: underline; }

                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 16px 0;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                th {
                    background-color: #2c3e50;
                    color: white;
                    font-weight: 600;
                    padding: 12px 15px;
                    text-align: left;
                    border: none;
                }
                td {
                    padding: 10px 15px;
                    border-bottom: 1px solid #e0e0e0;
                    background-color: #ffffff;
                }
                tr:hover td { background-color: #f5f5f5; }
                tr:nth-child(even) td { background-color: #f9f9f9; }
                tr:nth-child(even):hover td { background-color: #f0f0f0; }
                td:first-child { font-weight: 500; color: #2c3e50; }
                table code { background-color: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }
            </style>
            """
            
            html = style_fix + html
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
        scroll_pos = self.text_browser.verticalScrollBar().value()
        self.text_browser.setHtml(updated_html)
        self.text_browser.verticalScrollBar().setValue(scroll_pos)

