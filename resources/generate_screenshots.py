import sys
import os
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ui.main_window import MainWindowClass

def generate_all():
    """Dynamically cycles through themes and views to export complete screenshot pack."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindowClass()
    window.resize(1280, 720)
    
    # Setup absolute base directory for output
    base_dir = Path(__file__).parent.parent / "resources" / "screenshots"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Initiating Auto-Snap Engine targeting: {base_dir}")
    
    # Execution queue: (Theme, ViewModeMethod, FilenameSuffix)
    tasks = [
        ("light", window.show_chat_mode, "Main_Window_Light.png"),
        ("dark",  window.show_chat_mode, "Main_Window_Dark.png"),
        ("light", window.show_arena_mode, "Arena_Mode_Light.png"),
        ("dark",  window.show_arena_mode, "Arena_Mode_Dark.png"),
    ]
    
    def process_next_task(queue):
        if not queue:
            print("\n🎉 ALL SNAPS COMPLETED SUCCESSFULLY.")
            window.close()
            app.quit()
            return
            
        theme, view_fn, filename = queue.pop(0)
        print(f"📸 Capturing {view_fn.__name__} in {theme.upper()}...")
        
        # 1. Apply Visual State
        window.theme_manager.apply_theme(theme)
        view_fn()
        window.show()
        
        # 2. Allow layout to breathe, then snap
        def snap():
            save_path = base_dir / filename
            pixmap = window.grab()
            if pixmap.save(str(save_path), "PNG"):
                print(f"   ✅ Saved -> {filename}")
            else:
                print(f"   ❌ FAILED -> {filename}")
            
            # Process next after slight delay for UI safety
            QTimer.singleShot(500, lambda: process_next_task(queue))
            
        QTimer.singleShot(800, snap)

    # Kick off first task
    process_next_task(tasks)
    sys.exit(app.exec())

if __name__ == "__main__":
    # Ensure we can resolve root imports when running from resources folder
    sys.path.append(str(Path(__file__).parent.parent))
    generate_all()
