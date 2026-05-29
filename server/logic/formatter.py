# logic/formatter.py
import re
import markdown
import base64

class MessageFormatter:
    """
    Handles the conversion of raw AI markdown responses into rich HTML 
    with syntax-highlighted code blocks, copy buttons, and proper theme-aware styling.
    """
    def __init__(self, theme_manager):
        self.theme_manager = theme_manager

    def format_ai_response(self, text: str) -> str:
        """
        Parses markdown text, extracts code blocks, and returns a rich HTML string.
        """
        # Regex to find fenced code blocks
        code_block_pattern = re.compile(r'```(\w*)\n([\s\S]*?)\n```')

        def replacer(match):
            lang = match.group(1)
            code = match.group(2)
            lang_display = lang.upper() if lang else "CODE"

            # Base64 encode the code for the copy link
            encoded_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')

            # Get theme-specific colors
            if self.theme_manager.current_theme == "dark":
                header_bg = "#2d2d2d"
                header_text = "#cccccc"
                header_border = "#3c3c3c"
                link_color = "#4fc3f7"
                code_bg = "#1e1e1e" 
                code_text = "#d4d4d4"
            else:
                header_bg = "#f0f0f0"
                header_text = "#333333"
                header_border = "#cccccc"
                link_color = "#0078d4"
                code_bg = "#ffffff" 
                code_text = "#333333"

            wrapper_style = f"background-color: {code_bg}; border: 1px solid {header_border}; border-radius: 5px; overflow: hidden; margin: 10px 0; font-family: Consolas, monospace;"

            run_link = ""
            if lang.lower() in ['python', 'py', 'python3']:
                run_link = f'<a href="run_code:{encoded_code}" style="color: #4caf50; text-decoration: none; font-weight: 900; margin-right: 15px; cursor: pointer;">▶️ Run Python</a>'

            header_div = f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 10px; border-bottom: 1px solid {header_border}; font-size: 12px; font-weight: bold; background-color: {header_bg}; color: {header_text};">
                <span>{lang_display}</span>
                <div style="display: flex; gap: 10px;">
                    {run_link}
                    <a href="copy_code:{encoded_code}" style="color: {link_color}; text-decoration: none; cursor: pointer;">📋 Copy</a>
                </div>
            </div>
            """

            # Convert markdown to HTML (Syntax Highlighting)
            inner_html = markdown.markdown(f"```{lang}\n{code}\n```", extensions=['codehilite', 'fenced_code'])
            
            # Inject inline styles into the <pre> tag to force background and text color
            inner_html = inner_html.replace('<pre', f'<pre style="background-color: {code_bg}; color: {code_text}; margin: 0; border: none; border-radius: 0;"')
            
            content_div = f'<div style="overflow-x: auto;">{inner_html}</div>'

            return f'<div style="{wrapper_style}">{header_div}{content_div}</div>'

        # Process the text
        parts = []
        last_pos = 0
        
        for match in code_block_pattern.finditer(text):
            # 1. Add text before code block
            if match.start() > last_pos:
                normal_text = text[last_pos:match.start()]
                parts.append(markdown.markdown(normal_text, extensions=['extra', 'codehilite', 'fenced_code']))

            # 2. Add processed code block
            parts.append(replacer(match))
            last_pos = match.end()

        # 3. Add remaining text
        if last_pos < len(text):
            normal_text = text[last_pos:]
            parts.append(markdown.markdown(normal_text, extensions=['extra', 'codehilite', 'fenced_code']))

        return "".join(parts)

    def escape_html(self, text: str) -> str:
        """Helper to escape HTML characters in strings."""
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in text)
