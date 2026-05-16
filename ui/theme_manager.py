# ui/theme_manager.py
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QSystemTrayIcon, QMessageBox, QApplication
from utils.path_utils import get_resource_path, get_app_settings

class ThemeManager:
    """
    Handles all styling, CSS, and theme-switching logic for the application.
    Extracting this from MainWindowClass reduces complexity and improves maintainability.
    """
    def __init__(self, main_window):
        self.window = main_window
        self.current_theme = "light"

    def apply_theme(self, theme: str):
        """Apply dark or light theme to the entire window and its components."""
        self.current_theme = theme
        get_app_settings().setValue("theme", theme)

        # Set theme attribute for QSS selectors
        self.window.setProperty("theme", theme)
        self.window.style().unpolish(self.window)
        self.window.style().polish(self.window)

        # Load the global QSS file
        qss_file = get_resource_path("resources/styles.qss")
        if qss_file.exists():
            with open(qss_file, 'r', encoding='utf-8') as f:
                self.window.setStyleSheet(f.read())

        # Update UI components across active dynamic container
        self._update_toggle_button()
        self._apply_menu_bar_theme()
        self.refresh_auth_button_style()
        self._apply_placeholder_styles()
        
        # Broadcast specific display updates to all dynamic modules in stack
        try:
            for i in range(self.window.ui.main_stack.count()):
                view = self.window.ui.main_stack.widget(i)
                if hasattr(view, "chat_display"):
                    view.chat_display.setStyleSheet(self.get_chat_styles())
                if hasattr(view, "chat_a"):
                    view.chat_a.setStyleSheet(self.get_chat_styles())
                if hasattr(view, "chat_b"):
                    view.chat_b.setStyleSheet(self.get_chat_styles())
        except Exception as e:
            print(f"[ThemeManager] Failed to propagate text stylesheets: {e}")

    def toggle_theme(self):
        """Switch between dark and light theme."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)

    def _get_active_view(self):
        try:
            return self.window.ui.main_stack.currentWidget()
        except:
            return None

    def _update_toggle_button(self):
        text = "🌙" if self.current_theme == "dark" else "☀️"
        # Broad cast update to all currently loaded views
        try:
            for i in range(self.window.ui.main_stack.count()):
                w = self.window.ui.main_stack.widget(i)
                if hasattr(w, "theme_toggle_btn"):
                    w.theme_toggle_btn.setText(text)
        except: pass

    def _apply_placeholder_styles(self):
        """Dynamically overrides palette role for placeholder text to guarantee high-contrast readability."""
        from PySide6.QtGui import QPalette, QColor
        
        # High-contrast grey values specifically tuned for accessibility
        # In dark mode: Bright soft-grey (#a0a0a0) ensuring visibility against #2d2d2d
        # In light mode: Deep charcoal-grey (#666666) ensuring visibility against #f5f5f5
        color = QColor("#a0a0a0") if self.current_theme == "dark" else QColor("#666666")
        
        try:
            for i in range(self.window.ui.main_stack.count()):
                view = self.window.ui.main_stack.widget(i)
                target_input = None
                
                # Search for direct or nested input field handles
                if hasattr(view, "input_field"):
                    target_input = view.input_field
                elif hasattr(view, "ui") and hasattr(view.ui, "input_field"):
                    target_input = view.ui.input_field
                    
                if target_input:
                    palette = target_input.palette()
                    palette.setColor(QPalette.PlaceholderText, color)
                    target_input.setPalette(palette)
                    target_input.update() # Force visual redraw
        except Exception as e:
             print(f"[ThemeManager] Failed to set placeholder colors: {e}")


    def _apply_menu_bar_theme(self):
        if self.current_theme == "dark":
            self.window.menuBar().setStyleSheet("""
                QMenuBar { background-color: #1e1e1e; color: #d4d4d4; }
                QMenuBar::item:selected { background-color: #0078d4; }
                QMenu { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; }
                QMenu::item:selected { background-color: #0078d4; }
            """)
        else:
            self.window.menuBar().setStyleSheet("""
                QMenuBar { background-color: #ffffff; color: #333333; border-bottom: 1px solid #e0e0e0; }
                QMenuBar::item:selected { background-color: #0078d4; color: white; }
                QMenu { background-color: #ffffff; color: #333333; border: 1px solid #e0e0e0; }
                QMenu::item:selected { background-color: #0078d4; color: white; }
            """)

    def refresh_auth_button_style(self):
        """Broadcasts auth button style update to all dynamic UI layers."""
        has_key = self.window.llm_client.is_globally_authenticated()
        txt = "🚪 Logout" if has_key else "🔓 Login"
        bg = "#d32f2f" if has_key else "#0078d4"
        hv = "#b71c1c" if has_key else "#106ebe"
        
        style = f"QPushButton {{ background-color: {bg}; border: none; border-radius: 5px; padding: 8px 20px; color: white; font-weight: bold; }} QPushButton:hover {{ background-color: {hv}; }}"
        
        try:
            for i in range(self.window.ui.main_stack.count()):
                w = self.window.ui.main_stack.widget(i)
                if hasattr(w, "auth_btn"):
                    w.auth_btn.setText(txt)
                    w.auth_btn.setStyleSheet(style)
        except: pass

    def _update_send_button_style(self):
        # Send button styles are managed explicitly by the Views in modular design.
        pass

    def get_chat_styles(self):
        """Return full chat display stylesheet based on current theme."""
        if self.current_theme == "dark":
            return """
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    border: none;
                    padding: 20px;
                    font-size: 15px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                p { margin: 8px 0; line-height: 1.6; }
                b, strong { color: #ffffff; font-weight: 600; }
                i, em { color: #b0b0b0; }
                ul, ol { margin-left: 20px; margin-top: 5px; margin-bottom: 5px; }
                li { margin-bottom: 4px; }
                blockquote {
                    border-left: 4px solid #0078d4;
                    background-color: #252526;
                    padding: 10px 15px;
                    margin: 10px 0;
                    border-radius: 0 5px 5px 0;
                    color: #cccccc;
                }
                table {
                    border-collapse: collapse;
                    margin: 10px 0;
                    width: 100%;
                    background-color: #252526;
                    border-radius: 5px;
                    overflow: hidden;
                }
                th, td {
                    border: 1px solid #404040;
                    padding: 8px 12px;
                    text-align: left;
                }
                th { background-color: #2d2d2d; color: #ffffff; font-weight: bold; }
                code:not(pre code) {
                    background-color: #2d2d2d;
                    color: #ce9178;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 13px;
                }   
                b { font-size: 14px; }
            """
        else:
            return """
                QTextEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: none;
                    padding: 20px;
                    font-size: 15px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                p { margin: 8px 0; line-height: 1.6; }
                b, strong { color: #000000; font-weight: 600; }
                i, em { color: #666666; }
                ul, ol { margin-left: 20px; margin-top: 5px; margin-bottom: 5px; }
                li { margin-bottom: 4px; }
                blockquote {
                    border-left: 4px solid #0078d4;
                    background-color: #f5f5f5;
                    padding: 10px 15px;
                    margin: 10px 0;
                    border-radius: 0 5px 5px 0;
                    color: #555555;
                }
                table {
                    border-collapse: collapse;
                    margin: 10px 0;
                    width: 100%;
                    background-color: #ffffff;
                    border-radius: 5px;
                    overflow: hidden;
                    border: 1px solid #e0e0e0;
                }
                th, td {
                    border: 1px solid #e0e0e0;
                    padding: 8px 12px;
                    text-align: left;
                }
                th { background-color: #f5f5f5; color: #333333; font-weight: bold; }
                code:not(pre code) {
                    background-color: #f0f0f0;
                    color: #d63384;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 13px;
                }   
                b { font-size: 14px; }
            """

    def get_system_message_color(self):
        return "#ffd700" if self.current_theme == "dark" else "#0078d4"

    def get_terminate_color(self):
        return "#ff9800" if self.current_theme == "dark" else "#e65100"

    def get_thinking_color(self):
        return "#888" if self.current_theme == "dark" else "#888888"

    def get_code_block_style(self):
        if self.current_theme == "dark":
            return 'background-color: #1e1e1e; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;'
        else:
            return 'background-color: #f5f5f5; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;'

    def get_code_text_style(self):
        return "font-family: Consolas, monospace; color: #d4d4d4;" if self.current_theme == "dark" else "font-family: Consolas, monospace; color: #333333;"

    def get_metrics_border_color(self):
        return "#3c3c3c" if self.current_theme == "dark" else "#e0e0e0"

    def get_status_badge_style(self, status: str):
        """Unified 'WOW' badge styling for status labels."""
        is_dark = self.current_theme == "dark"
        s = status.upper().strip()
        
        # Color Palettes
        if s in ["ACTIVE", "FREE", "OK"]:
            bg = "#1e3a1e" if is_dark else "#e8f5e9"
            fg = "#00E676" if is_dark else "#2e7d32"
        elif s in ["AVAILABLE", "PAID", "UPGRADE"]:
            bg = "#1a237e" if is_dark else "#e8eaf6"
            fg = "#448aff" if is_dark else "#1a237e"
        else: # UNAVAILABLE / ERROR / MISSING
            bg = "#3d1b1b" if is_dark else "#ffebee"
            fg = "#ff5252" if is_dark else "#c62828"
            
        return f"background-color: {bg}; color: {fg}; border: 1px solid {fg}; border-radius: 4px; font-weight: bold; padding: 2px 8px;"


    def get_copy_button_html(self):
        blue = "#0078d4" if self.current_theme == "dark" else "#0056b3"
        orange = "#ff9800" if self.current_theme == "dark" else "#e65100"
        return (
            f'<div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">'
            f'<a href="regenerate" style="display: inline-block; border: 1px solid {orange}; background-color: rgba(255, 152, 0, 0.1); color: {orange}; padding: 6px 15px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold;">🔄 Regenerate</a>'
            f'<a href="copy" style="display: inline-block; border: 1px solid {blue}; background-color: rgba(0, 120, 212, 0.1); color: {blue}; padding: 6px 15px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold;">📋 Copy Raw</a>'
            f'</div>'
        )
