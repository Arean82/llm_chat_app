# operator_tools/companion/companion_operation.py
# Standalone Companion Operation App (Phase 11.4)
# Dual-Mode: Multi-Tab GUI Wizard + Headless CLI Terminal

import sys
import os
import shutil
import argparse
import configparser
from pathlib import Path
import datetime

if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
    UI_ASSETS_DIR = getattr(sys, '_MEIPASS', ROOT_DIR)
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UI_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "ui_assets")

sys.path.insert(0, ROOT_DIR)

from core.local_relocator import LocalRelocatorCore
from core.service_installer import ServiceInstallerCore

def check_admin_access() -> bool:
    """Pre-flight check to verify write permissions for config.ini."""
    saas_dir = os.path.join(ROOT_DIR, "saas")
    config_path = os.path.join(saas_dir, "config.ini")
    os.makedirs(saas_dir, exist_ok=True)
    try:
        if os.path.exists(config_path):
            with open(config_path, 'a') as f: pass
        else:
            with open(config_path, 'w') as f: pass
        return True
    except PermissionError:
        return False

def save_config(driver, credentials):
    """Saves the verified credentials to saas/config.ini"""
    config_path = os.path.join(ROOT_DIR, "saas", "config.ini")
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    if not config.has_section("TENANT_DB"):
        config.add_section("TENANT_DB")
        
    config.set("TENANT_DB", "driver", driver)
    
    if driver == "postgres":
        config.set("TENANT_DB", "pg_connection_string", credentials.get('pgConnStr', ''))
    elif driver == "mysql":
        config.set("TENANT_DB", "mysql_host", credentials.get('myHost', '127.0.0.1'))
        config.set("TENANT_DB", "mysql_port", credentials.get('myPort', '3306'))
        config.set("TENANT_DB", "mysql_user", credentials.get('myUser', 'root'))
        config.set("TENANT_DB", "mysql_password", credentials.get('myPass', ''))
        config.set("TENANT_DB", "mysql_database", credentials.get('myDB', 'saas_tenants'))
        
    with open(config_path, 'w') as f:
        config.write(f)

# ═══════════════════════════════════════════════════════════════════
#  HEADLESS / CLI MODE
# ═══════════════════════════════════════════════════════════════════

def run_headless_migration(args=None):
    print("======================================================================")
    print(" 🛠️  COMPANION OPERATION / ADMIN DASHBOARD (CLI MODE)")
    print("======================================================================")
    
    if not check_admin_access():
        print("❌ CRITICAL: Access Denied to saas/config.ini.")
        print("Please restart this terminal as Administrator.")
        return 1
        
    if args and getattr(args, 'action', None):
        print(f"Executing automated action: {args.action}")
        if args.action == "backup":
            return _run_backup_cli(getattr(args, 'target_dir', None))
        elif args.action == "relocate":
            print("Action 'relocate' currently requires interactive prompts.")
            return 1
        elif args.action == "web-config":
            host = getattr(args, 'host', None)
            port_str = getattr(args, 'port', None)
            if not host or not port_str:
                print("❌ Error: --host and --port are required for 'web-config' action.")
                return 1
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError()
            except ValueError:
                print("❌ Error: Invalid port value.")
                return 1
            from web.core.config_manager import SaaSConfigManager
            config = SaaSConfigManager()
            config.set_val("NETWORK", "host", host)
            config.set_val("NETWORK", "port", str(port))
            config.set_local_url(host, port)
            config.save()
            print(f"✅ Network configuration successfully updated to http://{host}:{port}")
            return 0
        else:
            print(f"Unknown action: {args.action}")
            return 1
            
    while True:
        print("\nMain Menu:")
        print("  1. 📦 SaaS DB Relocator (Turso → Enterprise SQL)")
        print("  2. 📂 Local Storage Relocator")
        print("  3. ⚙️ Background Service Installation")
        print("  4. 💾 Backup Local SaaS Database")
        print("  5. 🌐 Network/Web Config")
        print("  6. Exit")
        choice = input("\nSelect operation (1-6) [6]: ").strip() or "6"
        
        if choice == "6":
            print("\nExiting. Goodbye.")
            return 0
            
        if choice == "1":
            _run_saas_tenant_relocation_cli()
        elif choice == "2":
            _run_local_relocator_cli()
        elif choice == "3":
            _run_service_installer_cli()
        elif choice == "4":
            _run_backup_cli()
        elif choice == "5":
            _run_web_settings_cli()
        else:
            print("Invalid choice.")

def _run_backup_cli(target_dir=None):
    db_path = os.path.join(ROOT_DIR, "saas_tenants.db")
    if not os.path.exists(db_path):
        print("❌ Local Turso Database not found at:", db_path)
        return 1
    
    dest = target_dir
    if not dest:
        dest = input("Enter backup destination folder path: ").strip()
        
    if not dest or not os.path.exists(dest):
        print("Invalid directory.")
        return 1
        
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_file = os.path.join(dest, f"saas_tenants_backup_{stamp}.db")
    try:
        shutil.copy2(db_path, target_file)
        print(f"✅ Database backed up to: {target_file}")
        return 0
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return 1

def _run_local_relocator_cli():
    core = LocalRelocatorCore()
    print("\n--- Local Storage Relocator ---")
    print(f"Current Root: {core.get_current_root()}")
    print(core.calculate_storage_size())
    print("\nTarget Options:")
    print("  1. Portable (Program Folder)")
    print("  2. AppData (System Profile)")
    
    choice = input("Select target (1-2): ").strip()
    if choice not in ["1", "2"]:
        print("Aborted.")
        return
        
    target = core.storage_mgr.get_exe_dir() if choice == "1" else core.storage_mgr.get_default_app_data_path()
    mode = "PORTABLE" if choice == "1" else "APPDATA"
    
    confirm = input(f"Migrate to {target}? (y/n): ").strip().lower()
    if confirm == 'y':
        print("Migrating...")
        success, msg = core.execute_migration(mode, target)
        print(f"[{'SUCCESS' if success else 'FAILED'}] {msg}")

def _run_service_installer_cli():
    core = ServiceInstallerCore()
    print("\n--- Background Service Installer ---")
    os_choice = input("Target OS (1=Windows, 2=Linux) [1]: ").strip() or "1"
    os_target = "windows" if os_choice == "1" else "linux"
    
    name = input("Service Name [llm-chat-backend]: ").strip() or "llm-chat-backend"
    desc = input("Description: ").strip() or "Background API daemon"
    
    start_choice = input("Startup (1=Auto, 2=Manual) [1]: ").strip() or "1"
    start_type = "auto" if start_choice == "1" else "demand"
    
    user = "root"
    group = "root"
    policy = "on-failure"
    restart_sec = "5"
    start_delay = "0"
    log_dir = "/var/log/llm-chat-backend"
    env_file = "/etc/llm-chat-backend/.env"
    hardening = True
    
    if os_target == "linux":
        user = input("Linux User [root]: ").strip() or "root"
        group = input("Linux Group [root]: ").strip() or "root"
        policy = input("Restart Policy (on-failure/always/no) [on-failure]: ").strip() or "on-failure"
        restart_sec = input("Restart Delay in sec [5]: ").strip() or "5"
        start_delay = input("Startup Delay in sec [0]: ").strip() or "0"
        log_dir = input("Log Directory [/var/log/llm-chat-backend]: ").strip() or "/var/log/llm-chat-backend"
        env_file = input("Env File [/etc/llm-chat-backend/.env]: ").strip() or "/etc/llm-chat-backend/.env"
        h = input("Apply Security Hardening? (y/n) [y]: ").strip().lower()
        hardening = False if h == 'n' else True
    else:
        user = input("Windows Service User [MyAppUser]: ").strip() or "MyAppUser"
        group = input("Windows User Password: ").strip()
        policy = input("Restart Policy (on-failure/always/no) [on-failure]: ").strip() or "on-failure"
        restart_sec = input("Restart Delay in sec [5]: ").strip() or "5"
        start_delay = input("Startup Delay in sec [0]: ").strip() or "0"
        log_dir = input("Log Directory [logs]: ").strip() or "logs"
        env_file = input("Env File [.env]: ").strip() or ".env"
    
    success, msg = core.generate_installer(os_target, name, desc, start_type, user, group, policy, restart_sec, start_delay, log_dir, env_file, hardening)
    print(f"\n[{'SUCCESS' if success else 'FAILED'}] {msg}")

def _run_saas_tenant_relocation_cli():
    print("\n--- SaaS Tenant Upgrader ---")
    print("Source: Local Turso DB (saas_tenants.db)")
    print("\nSelect Target Driver:")
    print("1. PostgreSQL")
    print("2. MySQL / MariaDB")
    driver_choice = input("Choice (1-2) [1]: ").strip() or "1"
    
    credentials = {}
    driver = "postgres" if driver_choice == "1" else "mysql"
    
    credentials['myHost'] = input("Host [127.0.0.1]: ").strip() or "127.0.0.1"
    credentials['myPort'] = input("Port (5432 for PG, 3306 for MySQL): ").strip()
    if not credentials['myPort']:
        credentials['myPort'] = "5432" if driver == "postgres" else "3306"
        
    credentials['myUser'] = input("User: ").strip() or ("postgres" if driver == "postgres" else "root")
    credentials['myPass'] = input("Password: ").strip()
    credentials['myDB'] = input("Database [saas_tenants]: ").strip() or "saas_tenants"
    
    if driver == "postgres":
        credentials['pgConnStr'] = f"postgresql://{credentials['myUser']}:{credentials['myPass']}@{credentials['myHost']}:{credentials['myPort']}/{credentials['myDB']}"

    confirm = input("\nProceed with migration? (y/n) [n]: ").strip().lower()
    if confirm != 'y': return
    
    print("\nRunning pre-flight database connection check...")
    try:
        if driver == "postgres":
            try:
                import importlib
                psycopg2 = importlib.import_module("psycopg2")
                conn = psycopg2.connect(credentials['pgConnStr'], connect_timeout=5)
                conn.close()
                print("✅ Pre-flight connection test: Connection successful!")
            except ImportError:
                print("⚠️  Warning: psycopg2 package not installed. Skipping pre-flight connection check.")
        elif driver == "mysql":
            try:
                import importlib
                mysql_connector = importlib.import_module("mysql.connector")
                conn = mysql_connector.connect(
                    host=credentials['myHost'], port=int(credentials['myPort']),
                    user=credentials['myUser'], password=credentials['myPass'],
                    database=credentials['myDB'],
                    connection_timeout=5
                )
                conn.close()
                print("✅ Pre-flight connection test: Connection successful!")
            except ImportError:
                print("⚠️  Warning: mysql-connector-python package not installed. Skipping pre-flight connection check.")
    except Exception as check_err:
        print(f"❌ Pre-flight connection test: Connection failed! {check_err}")
        confirm_anyway = input("Do you want to proceed anyway? (y/n) [n]: ").strip().lower()
        if confirm_anyway != 'y':
            print("Migration aborted.")
            return

    try:
        from web.tenant_drivers.turso_tenant_driver import TursoTenantDriver
        source = TursoTenantDriver(db_name="saas_tenants.db")
        
        if driver == "postgres":
            from web.tenant_drivers.postgres_tenant_driver import PostgresTenantDriver
            target = PostgresTenantDriver(credentials['pgConnStr'])
        elif driver == "mysql":
            from web.tenant_drivers.mysql_tenant_driver import MySQLTenantDriver
            target = MySQLTenantDriver(
                host=credentials['myHost'], port=int(credentials['myPort']),
                user=credentials['myUser'], password=credentials['myPass'],
                database=credentials['myDB']
            )
            
        from server.logic.migration_bridge import migrate_saas_tenant_database, verify_saas_tenant_integrity
        
        count = migrate_saas_tenant_database(source, target, progress_callback=lambda log: print(f"  {log}"))
        print(f"✅ Relocated {count} tenants successfully.")
        
        print("Running Integrity Audit...")
        source_verify = TursoTenantDriver(db_name="saas_tenants.db")
        
        if driver == "postgres":
            from web.tenant_drivers.postgres_tenant_driver import PostgresTenantDriver
            target_verify = PostgresTenantDriver(credentials['pgConnStr'])
        elif driver == "mysql":
            from web.tenant_drivers.mysql_tenant_driver import MySQLTenantDriver
            target_verify = MySQLTenantDriver(
                host=credentials['myHost'], port=int(credentials['myPort']),
                user=credentials['myUser'], password=credentials['myPass'],
                database=credentials['myDB']
            )
            
        audit = verify_saas_tenant_integrity(source_verify, target_verify, progress_callback=lambda log: print(f"  {log}"))
        if audit["passed"]:
            save_config(driver, credentials)
            print("✅ Config updated successfully.")
        else:
            print("❌ Integrity audit failed. Config NOT updated.")
            
    except Exception as e:
        print(f"❌ Failed: {e}")

def _run_web_settings_cli():
    from web.core.config_manager import SaaSConfigManager
    config = SaaSConfigManager()
    print("\n--- Network/Web Config ---")
    current_host = config.get_str("NETWORK", "host", "127.0.0.1")
    current_port = config.get_str("NETWORK", "port", "8080")
    
    print(f"Current Host: {current_host}")
    print(f"Current Port: {current_port}")
    
    new_host = input(f"Enter new host address [{current_host}]: ").strip() or current_host
    new_port_str = input(f"Enter new listening port [{current_port}]: ").strip() or current_port
    
    try:
        new_port = int(new_port_str)
        if not (1 <= new_port <= 65535):
            raise ValueError()
    except ValueError:
        print("❌ Error: Invalid port. Must be an integer between 1 and 65535.")
        return
        
    config.set_val("NETWORK", "host", new_host)
    config.set_val("NETWORK", "port", str(new_port))
    config.set_local_url(new_host, new_port)
    config.save()
    print("✅ Network configuration updated successfully.")
    print("ℹ️  Note: You must restart the Web Portal service to apply changes.")

# ═══════════════════════════════════════════════════════════════════
#  GUI MODE
# ═══════════════════════════════════════════════════════════════════

def run_gui_migration():
    from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QTabWidget, 
                                   QPushButton, QMessageBox, QComboBox, QTextEdit, QProgressBar, QLabel, QFileDialog, QLineEdit)
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import QFile, QThread, Signal
    from PySide6.QtGui import QIcon
    import sys
    
    app = QApplication(sys.argv)
    
    style = """
    * {
        font-family: "Segoe UI", "Inter", "Roboto", "Helvetica Neue", Arial, sans-serif;
        font-size: 10pt;
    }
    QMainWindow, QDialog, QTabWidget::pane {
        background-color: #f8f9fa;
        border: none;
    }
    QTabBar::tab {
        background-color: #e9ecef;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background-color: #ffffff;
        border-bottom: 2px solid #0078d4;
        font-weight: bold;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        margin-top: 12px;
        background-color: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #0078d4;
    }
    QPushButton {
        background-color: #0078d4;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #106ebe;
    }
    QPushButton:pressed {
        background-color: #005a9e;
    }
    QPushButton:disabled {
        background-color: #a0a0a0;
    }
    QLineEdit, QComboBox {
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 6px;
        background-color: #ffffff;
    }
    QLineEdit:focus, QComboBox:focus {
        border: 1px solid #0078d4;
    }
    QProgressBar {
        border: 1px solid #ced4da;
        border-radius: 6px;
        text-align: center;
        background-color: #e9ecef;
        color: #495057;
        font-weight: bold;
    }
    QProgressBar::chunk {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #0078d4, stop: 1 #00b4ff);
        border-radius: 5px;
    }
    QTextEdit {
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 8px;
        font-family: "Consolas", "Courier New", monospace;
        color: #212529;
    }
    QLabel {
        color: #212529;
    }
    """
    app.setStyleSheet(style)
    
    if not check_admin_access():
        QMessageBox.critical(None, "Permission Denied", 
                             "Access to saas/config.ini is restricted.\n\n"
                             "Please right-click and 'Run as Administrator'.")
        return 1

    class SaasMigrationWorker(QThread):
        log_msg = Signal(str)
        prog_upd = Signal(int)
        finished = Signal(bool, str)
        
        def __init__(self, driver, credentials):
            super().__init__()
            self.driver = driver
            self.credentials = credentials
            
        def run(self):
            try:
                self.log_msg.emit("Connecting to Source (Turso)...")
                from web.tenant_drivers.turso_tenant_driver import TursoTenantDriver
                source = TursoTenantDriver(db_name="saas_tenants.db")
                
                self.log_msg.emit("Connecting to Target dynamically...")
                if self.driver == "postgres":
                    from web.tenant_drivers.postgres_tenant_driver import PostgresTenantDriver
                    target = PostgresTenantDriver(self.credentials['pgConnStr'])
                elif self.driver == "mysql":
                    from web.tenant_drivers.mysql_tenant_driver import MySQLTenantDriver
                    target = MySQLTenantDriver(
                        host=self.credentials['myHost'], port=int(self.credentials['myPort']),
                        user=self.credentials['myUser'], password=self.credentials['myPass'],
                        database=self.credentials['myDB']
                    )
                else:
                    self.finished.emit(False, "Unsupported target driver.")
                    return
                    
                from server.logic.migration_bridge import migrate_saas_tenant_database, verify_saas_tenant_integrity
                count = migrate_saas_tenant_database(source, target, progress_callback=lambda m: self.log_msg.emit(m))
                self.prog_upd.emit(70)
                
                self.log_msg.emit("Running Integrity Audit...")
                source_verify = TursoTenantDriver(db_name="saas_tenants.db")
                
                if self.driver == "postgres":
                    from web.tenant_drivers.postgres_tenant_driver import PostgresTenantDriver
                    target_verify = PostgresTenantDriver(self.credentials['pgConnStr'])
                elif self.driver == "mysql":
                    from web.tenant_drivers.mysql_tenant_driver import MySQLTenantDriver
                    target_verify = MySQLTenantDriver(
                        host=self.credentials['myHost'], port=int(self.credentials['myPort']),
                        user=self.credentials['myUser'], password=self.credentials['myPass'],
                        database=self.credentials['myDB']
                    )
                    
                audit = verify_saas_tenant_integrity(source_verify, target_verify, progress_callback=lambda m: self.log_msg.emit(m))
                self.prog_upd.emit(100)
                
                if audit["passed"]:
                    save_config(self.driver, self.credentials)
                    self.finished.emit(True, f"Relocated {count} accounts safely.\nconfig.ini successfully updated!")
                else:
                    self.finished.emit(False, "Integrity audit failed. config.ini was NOT updated to prevent data loss.")
            except Exception as e:
                self.finished.emit(False, str(e))

    class DashboardDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Administrator Dashboard")
            self.setMinimumSize(800, 600)
            
            loader = QUiLoader()
            dash_path = os.path.join(UI_ASSETS_DIR, "dashboard.ui")
            self.ui = loader.load(dash_path, self)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0,0,0,0)
            layout.addWidget(self.ui)
            
            self.mainTabs = self.ui.findChild(QTabWidget, "mainTabs")
            
            self.saas_tab = loader.load(os.path.join(UI_ASSETS_DIR, "saas_db.ui"), self)
            self.mainTabs.addTab(self.saas_tab, "📦 SaaS DB Relocator")
            self._wire_saas()
            
            self.local_tab = loader.load(os.path.join(UI_ASSETS_DIR, "local_relocator.ui"), self)
            self.mainTabs.addTab(self.local_tab, "📂 Local Storage Relocator")
            self._wire_local()
            
            self.service_tab = loader.load(os.path.join(UI_ASSETS_DIR, "service_installer.ui"), self)
            self.mainTabs.addTab(self.service_tab, "⚙️ Service Setup Wizard")
            self._wire_service()
            
            self.web_tab = loader.load(os.path.join(UI_ASSETS_DIR, "web_settings.ui"), self)
            self.mainTabs.addTab(self.web_tab, "🌐 Network Config")
            self._wire_web()
            
        def _wire_saas(self):
            self.saas_btn = self.saas_tab.findChild(QPushButton, "btn_start")
            self.btn_backup = self.saas_tab.findChild(QPushButton, "btn_backup")
            self.saas_log = self.saas_tab.findChild(QTextEdit, "log_output")
            self.saas_prog = self.saas_tab.findChild(QProgressBar, "progress_bar")
            self.saas_combo = self.saas_tab.findChild(QComboBox, "driverCombo")
            self.sourceInfoLabel = self.saas_tab.findChild(QLabel, "sourceInfoLabel")
            self.lbl_row_2 = self.saas_tab.findChild(QLabel, "label_2")
            
            if self.sourceInfoLabel:
                import configparser
                config_path = os.path.join(ROOT_DIR, "saas", "config.ini")
                driver_display = "Turso / libSQL (Local SQLite)\nsaas_tenants.db"
                if os.path.exists(config_path):
                    cp = configparser.ConfigParser()
                    cp.read(config_path)
                    if "Database" in cp and "driver" in cp["Database"]:
                        d = cp["Database"]["driver"]
                        if d == "postgres":
                            driver_display = f"PostgreSQL (psycopg2)\n{cp['Database'].get('host', 'localhost')}"
                            if self.lbl_row_2: self.lbl_row_2.setText(" Host :")
                            if self.btn_backup: self.btn_backup.setText("💾 Export PostgreSQL Database\n(Native Dump Tool)")
                        elif d == "mysql":
                            driver_display = f"MySQL / MariaDB (pymysql)\n{cp['Database'].get('host', 'localhost')}"
                            if self.lbl_row_2: self.lbl_row_2.setText(" Host :")
                            if self.btn_backup: self.btn_backup.setText("💾 Export MySQL Database\n(Native Dump Tool)")
                self.sourceInfoLabel.setText(driver_display)
            
            self.myHost = self.saas_tab.findChild(QLineEdit, "myHost")
            self.myPort = self.saas_tab.findChild(QLineEdit, "myPort")
            self.myUser = self.saas_tab.findChild(QLineEdit, "myUser")
            self.myPass = self.saas_tab.findChild(QLineEdit, "myPass")
            self.myDB = self.saas_tab.findChild(QLineEdit, "myDB")
            self.btn_eye = self.saas_tab.findChild(QPushButton, "btn_eye")
            
            defaults_path = os.path.join(ROOT_DIR, "saas", "defaults.ini")
            if os.path.exists(defaults_path):
                import configparser
                dp = configparser.ConfigParser()
                dp.read(defaults_path)
                if "TargetDatabase" in dp:
                    if self.myHost and "host" in dp["TargetDatabase"]: self.myHost.setText(dp["TargetDatabase"]["host"])
                    if self.myPort and "port" in dp["TargetDatabase"]: self.myPort.setText(dp["TargetDatabase"]["port"])
                    if self.myUser and "user" in dp["TargetDatabase"]: self.myUser.setText(dp["TargetDatabase"]["user"])
                    if self.myDB and "database" in dp["TargetDatabase"]: self.myDB.setText(dp["TargetDatabase"]["database"])
            
            from PySide6.QtGui import QIntValidator
            if self.myPort:
                self.myPort.setValidator(QIntValidator(1, 65535, self.saas_tab))
                
            if self.btn_eye and self.myPass:
                def toggle_password(checked):
                    if checked:
                        self.myPass.setEchoMode(QLineEdit.Normal)
                    else:
                        self.myPass.setEchoMode(QLineEdit.Password)
                self.btn_eye.toggled.connect(toggle_password)
            
            if self.saas_btn:
                self.saas_btn.clicked.connect(self._run_saas)
            if self.btn_backup:
                self.btn_backup.clicked.connect(self._run_backup)
                
        def _run_backup(self):
            import configparser
            import subprocess
            from PySide6.QtWidgets import QInputDialog, QLineEdit
            
            config_path = os.path.join(ROOT_DIR, "saas", "config.ini")
            driver = "sqlite"
            cp = configparser.ConfigParser()
            if os.path.exists(config_path):
                cp.read(config_path)
                if "Database" in cp and "driver" in cp["Database"]:
                    driver = cp["Database"]["driver"]
                    
            if driver == "sqlite":
                db_path = os.path.join(ROOT_DIR, "saas_tenants.db")
                if not os.path.exists(db_path):
                    QMessageBox.critical(self, "Error", "Local Turso DB not found.")
                    return
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                target_file, _ = QFileDialog.getSaveFileName(self, "Save Local Backup", f"saas_tenants_backup_{stamp}.db", "SQLite Database (*.db);;All Files (*)")
                if not target_file: return
                try:
                    shutil.copy2(db_path, target_file)
                    QMessageBox.information(self, "Backup Success", f"Database backed up to:\n{target_file}")
                except Exception as e:
                    QMessageBox.critical(self, "Backup Failed", str(e))
            else:
                db_user = cp['Database'].get('user', 'root')
                db_host = cp['Database'].get('host', '127.0.0.1')
                db_port = cp['Database'].get('port', '5432' if driver == 'postgres' else '3306')
                db_name = cp['Database'].get('database', 'saas_tenants')
                pwd = cp['Database'].get('password', '')
                
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if driver == "postgres":
                    formats = ["Plain Text (.sql)", "Custom Compressed (.dump) (Recommended)"]
                    format_choice, ok_fmt = QInputDialog.getItem(self, "PostgreSQL Dump Format", 
                                                                "Select backup format:\n(Compressed is recommended for use with pg_restore)", 
                                                                formats, 1, False)
                    if not ok_fmt: return
                    
                    if "Compressed" in format_choice:
                        target_file, _ = QFileDialog.getSaveFileName(self, "Save PostgreSQL Dump", f"backup_postgres_{stamp}.dump", "PostgreSQL Custom Dump (*.dump);;All Files (*)")
                        if not target_file: return
                        cmd = ["pg_dump", "-h", db_host, "-p", str(db_port), "-U", db_user, "-F", "c", "-f", target_file, db_name]
                    else:
                        target_file, _ = QFileDialog.getSaveFileName(self, "Save PostgreSQL Dump", f"backup_postgres_{stamp}.sql", "SQL Dump (*.sql);;All Files (*)")
                        if not target_file: return
                        cmd = ["pg_dump", "-h", db_host, "-p", str(db_port), "-U", db_user, "-F", "p", "-f", target_file, db_name]
                        
                    env = os.environ.copy()
                    env["PGPASSWORD"] = pwd
                else:
                    target_file, _ = QFileDialog.getSaveFileName(self, "Save MySQL Dump", f"backup_mysql_{stamp}.sql", "SQL Dump (*.sql);;All Files (*)")
                    if not target_file: return
                    cmd = ["mysqldump", "-h", db_host, "-P", str(db_port), "-u", db_user, f"-p{pwd}", "--result-file", target_file, db_name]
                    env = os.environ.copy()
                
                try:
                    from PySide6.QtCore import Qt
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
                    QApplication.restoreOverrideCursor()
                    QMessageBox.information(self, "Backup Success", f"Native SQL Dump generated successfully at:\n{target_file}")
                except subprocess.CalledProcessError as e:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "Backup Failed", f"Database dump failed:\n{e.stderr}")
                except FileNotFoundError:
                    QApplication.restoreOverrideCursor()
                    tool = "pg_dump" if driver == "postgres" else "mysqldump"
                    QMessageBox.critical(self, "Tool Not Found", f"The command-line tool '{tool}' is not installed or not available in the system PATH.\n\nPlease install the native database utilities to perform live backups.")
                except Exception as e:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{str(e)}")
            
        def _run_saas(self):
            index = self.saas_combo.currentIndex()
            driver = "postgres" if index == 0 else "mysql"
            
            creds = {}
            creds['myHost'] = self.myHost.text().strip() or "127.0.0.1"
            creds['myPort'] = self.myPort.text().strip() or ("5432" if driver == "postgres" else "3306")
            creds['myUser'] = self.myUser.text().strip() or ("postgres" if driver == "postgres" else "root")
            creds['myPass'] = self.myPass.text().strip()
            creds['myDB'] = self.myDB.text().strip() or "saas_tenants"

            if driver == "postgres":
                creds['pgConnStr'] = f"postgresql://{creds['myUser']}:{creds['myPass']}@{creds['myHost']}:{creds['myPort']}/{creds['myDB']}"

            reply = QMessageBox.question(self, "Confirm", "Start migration to the selected database?\n\nThis will safely rewrite saas/config.ini upon success.", QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes: return

            self.saas_btn.setEnabled(False)
            self.saas_log.clear()
            self.worker = SaasMigrationWorker(driver, creds)
            self.worker.log_msg.connect(self.saas_log.append)
            self.worker.prog_upd.connect(self.saas_prog.setValue)
            self.worker.finished.connect(self._saas_done)
            self.worker.start()
            
        def _saas_done(self, success, msg):
            self.saas_btn.setEnabled(True)
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Failed", msg)
                
        def _wire_local(self):
            self.local_core = LocalRelocatorCore()
            self.pathEdit = self.local_tab.findChild(object, "pathEdit")
            self.metricsLabel = self.local_tab.findChild(QLabel, "metricsLabel")
            self.relocateBtn = self.local_tab.findChild(QPushButton, "relocateBtn")
            
            if self.pathEdit: self.pathEdit.setText(str(self.local_core.get_current_root()))
            if self.metricsLabel: self.metricsLabel.setText(self.local_core.calculate_storage_size())
            if self.relocateBtn: self.relocateBtn.clicked.connect(self._run_local)
            
        def _run_local(self):
            items = ["Portable Mode", "Standard Mode", "Custom Network Drive"]
            from PySide6.QtWidgets import QInputDialog
            item, ok = QInputDialog.getItem(self, "Storage Strategy", "Select target:", items, 0, False)
            if not ok or not item: return
            
            mode = "PORTABLE" if "Portable" in item else "APPDATA"
            target = self.local_core.storage_mgr.get_exe_dir() if mode == "PORTABLE" else self.local_core.storage_mgr.get_default_app_data_path()
            
            if "Custom" in item:
                mode = "CUSTOM"
                dir_path = QFileDialog.getExistingDirectory(self, "Select Custom Folder")
                if not dir_path: return
                target = Path(dir_path)
                
            success, msg = self.local_core.execute_migration(mode, target)
            if success:
                QMessageBox.information(self, "Complete", "Relocation done. Restarting required.")
                sys.exit(0)
            else:
                QMessageBox.critical(self, "Failed", msg)

        def _wire_service(self):
            self.service_core = ServiceInstallerCore()
            self.srv_btn = self.service_tab.findChild(QPushButton, "generateBtn")
            self.srv_combo = self.service_tab.findChild(QComboBox, "startupTypeCombo")
            self.srv_out = self.service_tab.findChild(QLabel, "outputLabel")
            
            self.osCombo = self.service_tab.findChild(QComboBox, "osCombo")
            self.svcName = self.service_tab.findChild(QLineEdit, "svcName")
            self.svcDesc = self.service_tab.findChild(QLineEdit, "svcDesc")
            self.linuxUser = self.service_tab.findChild(QLineEdit, "linuxUser")
            self.linuxGroup = self.service_tab.findChild(QLineEdit, "linuxGroup")
            self.winUser = self.service_tab.findChild(QLineEdit, "winUser")
            self.winPass = self.service_tab.findChild(QLineEdit, "winPass")
            self.restartPolicy = self.service_tab.findChild(QComboBox, "restartPolicy")
            self.restartDelay = self.service_tab.findChild(QLineEdit, "restartDelay")
            self.startupDelay = self.service_tab.findChild(QLineEdit, "startupDelay")
            self.logDir = self.service_tab.findChild(QLineEdit, "logDir")
            self.envFile = self.service_tab.findChild(QLineEdit, "envFile")
            from PySide6.QtWidgets import QCheckBox
            self.hardeningCheck = self.service_tab.findChild(QCheckBox, "hardeningCheck")
            
            def validate_text():
                if self.logDir and self.osCombo.currentIndex() == 1:
                    val = self.logDir.text()
                    if val.startswith("/") and " " not in val:
                        self.logDir.setStyleSheet("border: 2px solid green;")
                    else:
                        self.logDir.setStyleSheet("border: 2px solid red;")
                elif self.logDir:
                    self.logDir.setStyleSheet("")
                    
                if self.envFile and self.osCombo.currentIndex() == 1:
                    val = self.envFile.text()
                    if val.startswith("/") and " " not in val:
                        self.envFile.setStyleSheet("border: 2px solid green;")
                    else:
                        self.envFile.setStyleSheet("border: 2px solid red;")
                elif self.envFile:
                    self.envFile.setStyleSheet("")
                    
                if self.linuxUser:
                    val = self.linuxUser.text()
                    if val.isalnum() or "-" in val or "_" in val:
                        self.linuxUser.setStyleSheet("border: 2px solid green;")
                    else:
                        self.linuxUser.setStyleSheet("border: 2px solid red;")

            if self.logDir: self.logDir.textChanged.connect(validate_text)
            if self.envFile: self.envFile.textChanged.connect(validate_text)
            if self.linuxUser: self.linuxUser.textChanged.connect(validate_text)
            
            def toggle_linux_fields(idx):
                is_linux = (idx == 1)
                is_win = (idx == 0)
                
                lbls_linux = ["labelLinuxUser", "labelLinuxGroup"]
                for l_name in lbls_linux:
                    lbl = self.service_tab.findChild(QLabel, l_name)
                    if lbl: lbl.setVisible(is_linux)
                
                lbls_win = ["labelWinUser", "labelWinPass"]
                for l_name in lbls_win:
                    lbl = self.service_tab.findChild(QLabel, l_name)
                    if lbl: lbl.setVisible(is_win)
                    
                if self.linuxUser: self.linuxUser.setVisible(is_linux)
                if self.linuxGroup: self.linuxGroup.setVisible(is_linux)
                
                if self.winUser: self.winUser.setVisible(is_win)
                if self.winPass: self.winPass.setVisible(is_win)
                
                if self.logDir: self.logDir.setText("/var/log/llm-chat-backend" if is_linux else "logs")
                if self.envFile: self.envFile.setText("/etc/llm-chat-backend/.env" if is_linux else ".env")
                
                validate_text()
                
            if self.osCombo:
                self.osCombo.currentIndexChanged.connect(toggle_linux_fields)
                toggle_linux_fields(0)
                
            if self.srv_btn:
                self.srv_btn.clicked.connect(self._generate_service)
                
        def _generate_service(self):
            st_type = "auto" if self.srv_combo.currentIndex() == 0 else "demand"
            os_target = "windows" if self.osCombo.currentIndex() == 0 else "linux"
            name = self.svcName.text().strip() or "llm-chat-backend"
            desc = self.svcDesc.text().strip() or "Background API daemon"
            
            policy = "on-failure"
            restart_sec = "5"
            start_delay = "0"
            log_dir = "logs"
            env_file = ".env"
            hardening = True
            
            if self.restartPolicy: policy = self.restartPolicy.currentText() or "on-failure"
            if self.restartDelay: restart_sec = self.restartDelay.text().strip() or "5"
            if self.startupDelay: start_delay = self.startupDelay.text().strip() or "0"
            if self.logDir: log_dir = self.logDir.text().strip()
            if self.envFile: env_file = self.envFile.text().strip()
            if self.hardeningCheck: hardening = self.hardeningCheck.isChecked()
            
            os_user = "root"
            os_pass = "root"
            
            if os_target == "windows":
                if self.winUser: os_user = self.winUser.text().strip() or "MyAppUser"
                if self.winPass: os_pass = self.winPass.text().strip()
                if not log_dir: log_dir = "logs"
                if not env_file: env_file = ".env"
            else:
                if self.linuxUser: os_user = self.linuxUser.text().strip() or "root"
                if self.linuxGroup: os_pass = self.linuxGroup.text().strip() or "root"
                if not log_dir: log_dir = "/var/log/llm-chat-backend"
                if not env_file: env_file = "/etc/llm-chat-backend/.env"
            
            success, msg = self.service_core.generate_installer(os_target, name, desc, st_type, os_user, os_pass, policy, restart_sec, start_delay, log_dir, env_file, hardening)
            self.srv_out.setText(msg)
            if success:
                self.srv_out.setStyleSheet("color: #3fb950; font-weight: bold;")
            else:
                self.srv_out.setStyleSheet("color: #ff7b72; font-weight: bold;")

        def _wire_web(self):
            from web.core.config_manager import SaaSConfigManager
            self.web_config = SaaSConfigManager()
            
            self.hostEdit = self.web_tab.findChild(QLineEdit, "hostEdit")
            self.portEdit = self.web_tab.findChild(QLineEdit, "portEdit")
            self.btn_save = self.web_tab.findChild(QPushButton, "btn_save")
            
            if self.hostEdit:
                self.hostEdit.setText(self.web_config.get_str("NETWORK", "host", "127.0.0.1"))
            if self.portEdit:
                self.portEdit.setText(self.web_config.get_str("NETWORK", "port", "8080"))
                
            from PySide6.QtGui import QIntValidator
            if self.portEdit:
                self.portEdit.setValidator(QIntValidator(1, 65535, self.web_tab))
                
            if self.btn_save:
                self.btn_save.clicked.connect(self._save_web_settings)
                
        def _save_web_settings(self):
            host = self.hostEdit.text().strip() if self.hostEdit else "127.0.0.1"
            port_str = self.portEdit.text().strip() if self.portEdit else "8080"
            
            if not host:
                QMessageBox.warning(self, "Validation Error", "Host Address cannot be empty.")
                return
            if not port_str:
                QMessageBox.warning(self, "Validation Error", "Port cannot be empty.")
                return
                
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError("Port out of range")
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Please enter a valid port between 1 and 65535.")
                return
                
            self.web_config.set_val("NETWORK", "host", host)
            self.web_config.set_val("NETWORK", "port", str(port))
            self.web_config.set_local_url(host, port)
            self.web_config.save()
            
            QMessageBox.information(self, "Settings Saved", "Network configuration updated successfully!\nPlease restart the Web Portal service to apply changes.")

    app.setApplicationName("Companion Operation")
    icon_path = os.path.join(ROOT_DIR, "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    dialog = DashboardDialog()
    dialog.show()
    return app.exec()

def main():
    parser = argparse.ArgumentParser(description="Companion Operation / Admin Dashboard")
    parser.add_argument("--headless", "--cli", action="store_true", dest="headless", help="Run in headless/CLI mode")
    parser.add_argument("--action", type=str, choices=["backup", "relocate", "web-config"], help="Automated scriptable action to perform")
    parser.add_argument("--target-dir", type=str, help="Target directory for backup")
    parser.add_argument("--host", type=str, help="Host for network configuration")
    parser.add_argument("--port", type=str, help="Port for network configuration")
    args = parser.parse_args()
    if args.headless:
        sys.exit(run_headless_migration(args))
    else:
        sys.exit(run_gui_migration())

if __name__ == "__main__":
    main()
