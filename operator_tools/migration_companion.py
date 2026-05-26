# operator_tools/migration_companion.py
# Standalone Migration Companion App (Phase 10.3)
# Dual-Mode: PySide6 Glassmorphic GUI Wizard + Headless CLI Terminal
# Designed for system service compatibility (Windows Services / systemd)
#
# Usage:
#   GUI Mode:    python operator_tools/migration_companion.py
#   CLI Mode:    python operator_tools/migration_companion.py --headless
#   CLI Mode:    python operator_tools/migration_companion.py --cli
#
# Frozen (exe):
#   GUI Mode:    "Migration Companion.exe"
#   CLI Mode:    "Migration Companion.exe" --headless

import sys
import os
import argparse
import time

# ─── Absolute service-friendly pathing resolution ───
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    # operator_tools/migration_companion.py -> project_root/
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, ROOT_DIR)


# ═══════════════════════════════════════════════════════════════════
#  HEADLESS / CLI MODE — No Qt dependency required
# ═══════════════════════════════════════════════════════════════════

def run_headless_migration():
    """
    Executes the full SaaS tenant database relocation pipeline in terminal mode.
    Ideal for remote daemons, automated services, and headless SaaS admin nodes.
    """
    print("\n" + "═" * 72)
    print("  🚀 MIGRATION COMPANION — HEADLESS / CLI MODE")
    print("═" * 72)
    print(f"Project Root: {ROOT_DIR}")
    print(f"Config Path:  {os.path.join(ROOT_DIR, 'saas', 'config.ini')}")
    print("─" * 72)

    # Step 1: Detect Source & Target
    print("\n[Step 1/5] Detecting active database driver configuration...")
    try:
        from saas.tenant_db import TenantDatabaseManager, _load_tenant_config
        config = _load_tenant_config()
        active_driver = config.get("driver", "turso")
        print(f"  Active Driver: {active_driver}")
    except Exception as e:
        print(f"  ❌ FATAL: Cannot load tenant configuration: {e}")
        return 1

    # Step 2: Menu Selection
    print("\n[Step 2/5] Select relocation operation:")
    print("  1. Chat Conversation History (Portable / AppData DBs)")
    print("  2. SaaS Tenant Metadata (Turso → Enterprise SQL)")
    print("  3. Exit")
    choice = input("\n  Enter choice (1-3) [3]: ").strip() or "3"

    if choice == "3":
        print("\n  Aborted by operator.")
        return 0

    if choice == "1":
        # Delegate to the existing interactive CLI bridge
        print("\n[Step 3/5] Launching Chat History Migration Bridge...")
        try:
            from logic.migration_bridge import run_interactive_cli_migration
            run_interactive_cli_migration()
        except Exception as e:
            print(f"\n  ❌ Migration bridge failed: {e}")
            return 1
        return 0

    if choice == "2":
        return _run_saas_tenant_relocation_cli()

    print(f"\n  ❌ Invalid selection: {choice}")
    return 1


def _run_saas_tenant_relocation_cli():
    """SaaS Tenant Metadata relocation (Turso → Postgres/MySQL) in CLI mode."""
    print("\n[Step 3/5] Preparing SaaS Tenant Metadata Relocation...")
    print("  ⚠️  Ensure saas/config.ini [TENANT_DB] section is configured with your TARGET driver.\n")

    confirm = input("  Proceed with relocation? (y/n) [n]: ").strip().lower()
    if confirm != "y":
        print("  Aborted by operator.")
        return 0

    try:
        # Source is always the local Turso/libSQL default
        from saas.tenant_drivers.turso_tenant_driver import TursoTenantDriver
        source = TursoTenantDriver()
        print("  ✅ Source (Turso/libSQL) connected.")

        # Destination is factory-configured from config.ini
        from saas.tenant_db import TenantDatabaseManager
        TenantDatabaseManager.reset_instance()
        target = TenantDatabaseManager()
        print(f"  ✅ Target ({target._driver.__class__.__name__}) connected.")

        # Step 4: Execute Migration
        print("\n[Step 4/5] Executing transactional relocation...")
        from logic.migration_bridge import migrate_saas_tenant_database
        count = migrate_saas_tenant_database(
            source, target,
            progress_callback=lambda log: print(f"    {log}")
        )
        print(f"\n  ✅ Relocation complete! {count} user accounts transferred.")

        # Step 5: Integrity Verification (Jaccard Similarity)
        print("\n[Step 5/5] Running post-relocation integrity audit...")

        # Reconnect fresh handles for verification (migration closes them)
        source_verify = TursoTenantDriver()
        TenantDatabaseManager.reset_instance()
        target_verify = TenantDatabaseManager()

        from logic.migration_bridge import verify_saas_tenant_integrity
        audit = verify_saas_tenant_integrity(
            source_verify, target_verify,
            progress_callback=lambda log: print(f"    {log}")
        )

        if audit["passed"]:
            print("\n  ✅ Integrity Audit PASSED — Zero data loss confirmed.")
            _print_jaccard_summary(audit)
        else:
            print("\n  ❌ Integrity Audit FAILED — Review mismatches above.")
            _print_jaccard_summary(audit)
            return 1

    except ImportError as e:
        print(f"\n  ❌ Missing dependency: {e}")
        print("     Ensure the target driver package is installed (psycopg2 / pymysql).")
        return 1
    except Exception as e:
        print(f"\n  ❌ Relocation error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "═" * 72)
    print("  🎉 Migration Companion — Operation completed successfully!")
    print("═" * 72 + "\n")
    return 0


def _print_jaccard_summary(audit: dict):
    """Prints a formatted Jaccard-style similarity summary table from audit results."""
    details = audit.get("details", {})
    if not details:
        return
    print("\n  ┌─────────────────────────┬────────┬────────┬─────────┐")
    print("  │ Table                   │ Source │ Target │ Match   │")
    print("  ├─────────────────────────┼────────┼────────┼─────────┤")
    for table, info in details.items():
        src = str(info["source_count"]).rjust(6)
        dst = str(info["dest_count"]).rjust(6)
        match = "  ✅" if info["match"] else "  ❌"
        print(f"  │ {table:<23} │ {src} │ {dst} │ {match}    │")
    print("  └─────────────────────────┴────────┴────────┴─────────┘")

    # Compute Jaccard Similarity Index
    total_tables = len(details)
    matched = sum(1 for d in details.values() if d["match"])
    jaccard = (matched / total_tables * 100) if total_tables > 0 else 0
    print(f"\n  Jaccard Similarity Index: {jaccard:.1f}% ({matched}/{total_tables} tables matched)")


# ═══════════════════════════════════════════════════════════════════
#  GUI MODE — PySide6 Glassmorphic Wizard
# ═══════════════════════════════════════════════════════════════════

def run_gui_migration():
    """
    Launches the PySide6-based glassmorphic wizard dialog for visual
    database relocation with progress indicators and real-time logging.
    """
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QTextEdit, QProgressBar, QComboBox, QGroupBox,
        QMessageBox, QFrame, QWidget
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer
    from PySide6.QtGui import QFont, QIcon

    class MigrationWorker(QThread):
        """Background worker thread for non-blocking database relocation."""
        log_message = Signal(str)
        progress_update = Signal(int)
        migration_complete = Signal(bool, str)

        def __init__(self, migration_type="saas"):
            super().__init__()
            self.migration_type = migration_type

        def run(self):
            try:
                if self.migration_type == "saas":
                    self._run_saas_migration()
                else:
                    self._run_chat_migration()
            except Exception as e:
                import traceback
                self.log_message.emit(f"❌ CRITICAL ERROR: {e}")
                self.log_message.emit(traceback.format_exc())
                self.migration_complete.emit(False, str(e))

        def _run_saas_migration(self):
            self.log_message.emit("Initializing SaaS Tenant Database Relocation...")
            self.progress_update.emit(5)

            # Source: Turso/libSQL
            self.log_message.emit("Connecting to source (Turso/libSQL)...")
            from saas.tenant_drivers.turso_tenant_driver import TursoTenantDriver
            source = TursoTenantDriver()
            self.log_message.emit("✅ Source connected.")
            self.progress_update.emit(15)

            # Target: Factory-configured driver
            self.log_message.emit("Connecting to target driver (from config.ini)...")
            from saas.tenant_db import TenantDatabaseManager
            TenantDatabaseManager.reset_instance()
            target = TenantDatabaseManager()
            driver_name = target._driver.__class__.__name__
            self.log_message.emit(f"✅ Target ({driver_name}) connected.")
            self.progress_update.emit(25)

            # Execute migration
            self.log_message.emit("Starting transactional data relocation...")
            from logic.migration_bridge import migrate_saas_tenant_database
            count = migrate_saas_tenant_database(
                source, target,
                progress_callback=lambda msg: self._on_bridge_log(msg)
            )
            self.progress_update.emit(70)
            self.log_message.emit(f"✅ Relocation complete: {count} user accounts transferred.")

            # Integrity verification
            self.log_message.emit("Running post-relocation integrity audit...")
            source_verify = TursoTenantDriver()
            TenantDatabaseManager.reset_instance()
            target_verify = TenantDatabaseManager()

            from logic.migration_bridge import verify_saas_tenant_integrity
            audit = verify_saas_tenant_integrity(
                source_verify, target_verify,
                progress_callback=lambda msg: self._on_bridge_log(msg)
            )
            self.progress_update.emit(95)

            if audit["passed"]:
                # Compute Jaccard score
                details = audit.get("details", {})
                total = len(details)
                matched = sum(1 for d in details.values() if d["match"])
                jaccard = (matched / total * 100) if total > 0 else 0
                self.log_message.emit(f"✅ Integrity Audit PASSED — Jaccard Similarity: {jaccard:.1f}%")
                self.progress_update.emit(100)
                self.migration_complete.emit(True, f"Successfully relocated {count} accounts. Integrity: {jaccard:.1f}%")
            else:
                self.log_message.emit("❌ Integrity Audit FAILED — Review logs above.")
                self.progress_update.emit(100)
                self.migration_complete.emit(False, "Integrity verification failed. Check logs.")

        def _run_chat_migration(self):
            self.log_message.emit("Chat History Migration requires interactive source/target configuration.")
            self.log_message.emit("Please use CLI mode (--headless) for chat history migration.")
            self.progress_update.emit(100)
            self.migration_complete.emit(False, "Chat migration requires CLI mode.")

        def _on_bridge_log(self, msg):
            self.log_message.emit(f"  {msg}")
            # Estimate progress based on keywords
            if "Migrating table:" in msg:
                current = self.progress_update  # rough increment
                # We'll let the main flow handle progress

    class MigrationCompanionDialog(QDialog):
        """
        Glassmorphic PySide6 wizard dialog for database relocation operations.
        Provides visual connection testing, migration progress, and integrity verification.
        """
        def __init__(self):
            super().__init__()
            self.setWindowTitle("🚀 Migration Companion — Database Relocator")
            self.setMinimumSize(720, 580)
            self.resize(780, 620)
            self.worker = None
            self._build_ui()
            self._apply_theme()

        def _build_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(12)

            # ── Header ──
            header = QLabel("🚀 Migration Companion")
            header.setFont(QFont("Segoe UI", 18, QFont.Bold))
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)

            subtitle = QLabel("Safely relocate SaaS tenant databases between storage engines")
            subtitle.setFont(QFont("Segoe UI", 10))
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setObjectName("subtitle")
            layout.addWidget(subtitle)

            # ── Separator ──
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setObjectName("separator")
            layout.addWidget(sep)

            # ── Configuration Panel ──
            config_group = QGroupBox("Relocation Configuration")
            config_group.setObjectName("config_group")
            config_layout = QVBoxLayout(config_group)

            # Migration type selector
            type_row = QHBoxLayout()
            type_label = QLabel("Migration Type:")
            type_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            type_row.addWidget(type_label)

            self.type_combo = QComboBox()
            self.type_combo.addItem("📦 SaaS Tenant Metadata (Turso → Enterprise SQL)")
            self.type_combo.addItem("💬 Chat Conversation History")
            self.type_combo.setMinimumHeight(32)
            type_row.addWidget(self.type_combo, 1)
            config_layout.addLayout(type_row)

            # Source info
            src_row = QHBoxLayout()
            src_label = QLabel("Source:")
            src_label.setFont(QFont("Segoe UI", 10))
            src_row.addWidget(src_label)
            self.src_info = QLabel("Turso / libSQL (local default)")
            self.src_info.setObjectName("info_label")
            src_row.addWidget(self.src_info, 1)
            config_layout.addLayout(src_row)

            # Target info
            tgt_row = QHBoxLayout()
            tgt_label = QLabel("Target:")
            tgt_label.setFont(QFont("Segoe UI", 10))
            tgt_row.addWidget(tgt_label)
            self.tgt_info = QLabel("Configured in saas/config.ini [TENANT_DB]")
            self.tgt_info.setObjectName("info_label")
            tgt_row.addWidget(self.tgt_info, 1)
            config_layout.addLayout(tgt_row)

            layout.addWidget(config_group)

            # ── Progress Section ──
            progress_group = QGroupBox("Relocation Progress")
            progress_group.setObjectName("progress_group")
            progress_layout = QVBoxLayout(progress_group)

            self.progress_bar = QProgressBar()
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(0)
            self.progress_bar.setMinimumHeight(28)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setFormat("%p% — Relocating...")
            progress_layout.addWidget(self.progress_bar)

            self.log_output = QTextEdit()
            self.log_output.setReadOnly(True)
            self.log_output.setFont(QFont("Consolas", 9))
            self.log_output.setMinimumHeight(200)
            self.log_output.setPlaceholderText("Migration logs will appear here...")
            progress_layout.addWidget(self.log_output)

            layout.addWidget(progress_group, 1)

            # ── Action Buttons ──
            btn_row = QHBoxLayout()
            btn_row.setSpacing(12)

            self.btn_start = QPushButton("▶  Start Relocation")
            self.btn_start.setMinimumHeight(40)
            self.btn_start.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self.btn_start.setCursor(Qt.PointingHandCursor)
            self.btn_start.setObjectName("btn_start")
            self.btn_start.clicked.connect(self.on_start)
            btn_row.addWidget(self.btn_start, 2)

            self.btn_close = QPushButton("✕  Close")
            self.btn_close.setMinimumHeight(40)
            self.btn_close.setFont(QFont("Segoe UI", 11))
            self.btn_close.setCursor(Qt.PointingHandCursor)
            self.btn_close.setObjectName("btn_close")
            self.btn_close.clicked.connect(self.close)
            btn_row.addWidget(self.btn_close, 1)

            layout.addLayout(btn_row)

            # Wire combo change
            self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        def _on_type_changed(self, index):
            if index == 0:
                self.src_info.setText("Turso / libSQL (local default)")
                self.tgt_info.setText("Configured in saas/config.ini [TENANT_DB]")
            else:
                self.src_info.setText("Interactive source selection required")
                self.tgt_info.setText("Interactive target selection required")

        def _apply_theme(self):
            self.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #0d1117, stop:0.5 #161b22, stop:1 #0d1117);
                    color: #c9d1d9;
                }
                QLabel {
                    color: #c9d1d9;
                }
                QLabel#subtitle {
                    color: #8b949e;
                    font-style: italic;
                }
                QLabel#info_label {
                    color: #58a6ff;
                    font-weight: bold;
                    padding: 4px 8px;
                    background: rgba(88, 166, 255, 0.08);
                    border-radius: 4px;
                }
                QFrame#separator {
                    color: #30363d;
                }
                QGroupBox {
                    font-weight: bold;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    margin-top: 16px;
                    padding: 16px 12px 12px 12px;
                    background: rgba(22, 27, 34, 0.7);
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 14px;
                    padding: 0 6px;
                    color: #58a6ff;
                }
                QComboBox {
                    background-color: #21262d;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                }
                QComboBox::drop-down {
                    border: none;
                    padding-right: 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #21262d;
                    color: #c9d1d9;
                    selection-background-color: #1f6feb;
                    border: 1px solid #30363d;
                }
                QProgressBar {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    text-align: center;
                    color: #c9d1d9;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1f6feb, stop:0.5 #58a6ff, stop:1 #1f6feb);
                    border-radius: 5px;
                }
                QTextEdit {
                    background-color: #0d1117;
                    color: #8b949e;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 8px;
                    selection-background-color: #1f6feb;
                }
                QPushButton#btn_start {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #238636, stop:1 #2ea043);
                    color: #ffffff;
                    border: 1px solid #2ea043;
                    border-radius: 8px;
                    padding: 8px 20px;
                }
                QPushButton#btn_start:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2ea043, stop:1 #3fb950);
                    border: 1px solid #3fb950;
                }
                QPushButton#btn_start:disabled {
                    background-color: #21262d;
                    color: #484f58;
                    border: 1px solid #30363d;
                }
                QPushButton#btn_close {
                    background-color: #21262d;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px 20px;
                }
                QPushButton#btn_close:hover {
                    background-color: #30363d;
                    border: 1px solid #484f58;
                }
            """)

        def on_start(self):
            """Trigger the relocation pipeline."""
            migration_type = "saas" if self.type_combo.currentIndex() == 0 else "chat"

            if migration_type == "chat":
                QMessageBox.information(
                    self, "CLI Required",
                    "Chat History Migration requires interactive terminal input.\n\n"
                    "Please run:\n  Migration Companion.exe --headless\n  or\n"
                    "  python operator_tools/migration_companion.py --headless"
                )
                return

            # Confirm
            reply = QMessageBox.question(
                self, "Confirm Relocation",
                "This will relocate ALL SaaS tenant data from the default Turso/libSQL "
                "database to the target driver configured in saas/config.ini.\n\n"
                "⚠️ The main LLM Chat App should be CLOSED to release database locks.\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            self.btn_start.setEnabled(False)
            self.btn_start.setText("⏳  Relocating...")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p% — Relocating...")
            self.log_output.clear()
            self.log_output.append("═" * 60)
            self.log_output.append("  Migration Companion — Relocation Started")
            self.log_output.append("═" * 60 + "\n")

            self.worker = MigrationWorker(migration_type=migration_type)
            self.worker.log_message.connect(self._append_log)
            self.worker.progress_update.connect(self._update_progress)
            self.worker.migration_complete.connect(self._on_complete)
            self.worker.start()

        def _append_log(self, msg):
            self.log_output.append(msg)
            # Auto-scroll to bottom
            sb = self.log_output.verticalScrollBar()
            sb.setValue(sb.maximum())

        def _update_progress(self, value):
            self.progress_bar.setValue(value)

        def _on_complete(self, success, message):
            self.btn_start.setEnabled(True)
            if success:
                self.btn_start.setText("✅  Relocation Complete")
                self.progress_bar.setFormat("100% — Complete!")
                self.log_output.append("\n" + "═" * 60)
                self.log_output.append("  🎉 Relocation completed successfully!")
                self.log_output.append("═" * 60)
                QMessageBox.information(self, "Success", f"Database relocation completed.\n\n{message}")
            else:
                self.btn_start.setText("▶  Retry Relocation")
                self.progress_bar.setFormat("Failed — Check Logs")
                self.log_output.append("\n" + "═" * 60)
                self.log_output.append("  ❌ Relocation failed. See logs above.")
                self.log_output.append("═" * 60)
                QMessageBox.critical(self, "Failed", f"Database relocation failed.\n\n{message}")

        def closeEvent(self, event):
            if self.worker and self.worker.isRunning():
                reply = QMessageBox.question(
                    self, "Migration Running",
                    "A relocation is currently in progress.\n\nForce quit?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    event.ignore()
                    return
                self.worker.terminate()
                self.worker.wait()
            event.accept()

    # Launch Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Migration Companion")
    app.setOrganizationName("Arean82")

    # Set app icon if available
    icon_path = os.path.join(ROOT_DIR, "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    dialog = MigrationCompanionDialog()
    dialog.show()
    return app.exec()


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="Migration Companion",
        description="Standalone Database Relocator for LLM Chat App — SaaS Tenant & Chat History Migration"
    )
    parser.add_argument(
        "--headless", "--cli",
        action="store_true",
        dest="headless",
        help="Run in headless/CLI terminal mode (no GUI). Ideal for remote servers and system services."
    )
    args = parser.parse_args()

    if args.headless:
        exit_code = run_headless_migration()
        sys.exit(exit_code)
    else:
        exit_code = run_gui_migration()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
