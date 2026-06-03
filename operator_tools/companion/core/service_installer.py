import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ServiceInstallerCore:
    """
    Decoupled headless logic for generating Windows (NSSM/PowerShell) or Linux (systemd/bash) Service installation scripts.
    Returns status tuples: (success: bool, message: str)
    """
    def __init__(self):
        pass
        
    def generate_installer(self, os_target: str, name: str, desc: str, start_type: str, 
                           os_user: str = "root", os_group_or_pass: str = "root", 
                           restart_policy: str = "on-failure", restart_sec: str = "5", startup_delay: str = "0",
                           log_dir: str = "logs", env_file: str = ".env", 
                           hardening: bool = True) -> tuple[bool, str]:
        """
        Generates either install_service.ps1 (Windows NSSM) or a .service file + install_service.sh (Linux)
        """
        try:
            current_dir = Path(os.path.abspath(os.path.dirname(__file__)))
            root_dir = current_dir.parent.parent.parent
            main_exe_path = root_dir / "Synora Studio.exe"
            
            # Executable Target
            if main_exe_path.exists():
                bin_path = f'"{main_exe_path}"'
                args = '--headless'
            else:
                main_py_path = root_dir / "main.py"
                bin_path = 'python'
                args = f'"{main_py_path}" --headless'

            if os_target == "windows":
                # NSSM / PowerShell logic
                start_nssm = "SERVICE_AUTO_START" if start_type == "auto" else "SERVICE_DEMAND_START"
                win_user = os_user
                win_pass = os_group_or_pass
                
                ps1_content = rf"""<#
.SYNOPSIS
Auto-generated PowerShell Installer for {name}
Uses NSSM (Non-Sucking Service Manager) to securely wrap the application.
#>

$ErrorActionPreference = "Stop"

# 1. Require Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {{
    Write-Warning "Please run this script as Administrator."
    Pause
    exit
}}

Write-Host "=== Installing Windows Service: {name} ==="

$AppDir = "{root_dir}"
$LogDir = "{log_dir}"
$EnvFile = "{env_file}"
$SvcUser = "{win_user}"
$SvcPass = "{win_pass}"

# 2. NSSM Auto-Download
$NssmExe = Join-Path $AppDir "nssm.exe"
if (-Not (Test-Path $NssmExe)) {{
    Write-Host "NSSM not found. Downloading the latest secure version..."
    $Url = "https://nssm.cc/release/nssm-2.24.zip"
    $ZipPath = Join-Path $AppDir "nssm.zip"
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath $AppDir -Force
    Copy-Item -Path (Join-Path $AppDir "nssm-2.24\win64\nssm.exe") -Destination $AppDir
    Remove-Item $ZipPath
    Remove-Item (Join-Path $AppDir "nssm-2.24") -Recurse
    Write-Host "NSSM downloaded successfully."
}} else {{
    Write-Host "NSSM executable found. (Update available? Checking manually is recommended)."
}}

# 3. Create Dedicated User
if (-Not (Get-LocalUser -Name $SvcUser -ErrorAction SilentlyContinue)) {{
    Write-Host "Creating dedicated service user: $SvcUser"
    $SecurePass = ConvertTo-SecureString $SvcPass -AsPlainText -Force
    New-LocalUser -Name $SvcUser -Password $SecurePass -PasswordNeverExpires -Description "Service Account for {name}"
}} else {{
    Write-Host "User $SvcUser already exists."
}}

# 4. Grant SeServiceLogonRight
Write-Host "Granting 'Log on as a service' rights to $SvcUser..."
# Using Secedit hack to apply user rights natively
$TempInf = "$env:TEMP\sec.inf"
$TempDb = "$env:TEMP\sec.sdb"
secedit /export /cfg $TempInf /quiet
(Get-Content $TempInf) -replace "^SeServiceLogonRight = .*", "$&,*$SvcUser" | Set-Content $TempInf
secedit /configure /db $TempDb /cfg $TempInf /quiet
Remove-Item $TempInf, $TempDb

# 5. Lock Down Permissions (icacls)
Write-Host "Applying strict permissions to Log and App directories..."
if (-Not (Test-Path $LogDir)) {{ New-Item -ItemType Directory -Path $LogDir }}
icacls "$LogDir" /grant "$($SvcUser):(OI)(CI)F" /T /C /Q
icacls "$AppDir" /grant "$($SvcUser):(OI)(CI)F" /T /C /Q

# 6. Install via NSSM
Write-Host "Configuring service via NSSM..."
# Remove if exists
& $NssmExe stop {name}
& $NssmExe remove {name} confirm

& $NssmExe install {name} "{bin_path}" {args}
& $NssmExe set {name} AppDirectory "$AppDir"
& $NssmExe set {name} Description "{desc}"
& $NssmExe set {name} Start $start_nssm

# Logging
& $NssmExe set {name} AppStdout "$LogDir\service.log"
& $NssmExe set {name} AppStderr "$LogDir\service_error.log"
& $NssmExe set {name} AppStdoutCreationDisposition 4
& $NssmExe set {name} AppStderrCreationDisposition 4

# Environment
if (Test-Path $EnvFile) {{
    $envLines = Get-Content $EnvFile | Where-Object {{ $_ -match "=" }}
    & $NssmExe set {name} AppEnvironmentExtra $envLines
}}

# Run As User
& $NssmExe set {name} ObjectName ".\$SvcUser" "$SvcPass"

# Restart Recovery
& $NssmExe set {name} AppExit Default Restart
& $NssmExe set {name} AppThrottle {restart_sec}000

Write-Host "Starting {name}..."
& $NssmExe start {name}

Write-Host "✅ Installation complete! Use Windows Services (services.msc) to view."
Pause
"""
                target_file = root_dir / f"install_{name}.ps1"
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(ps1_content)
                return True, f"Successfully generated Windows NSSM installer at:\n{target_file}\n\nPlease right-click and select 'Run with PowerShell' (as Administrator)."
                
            elif os_target == "linux":
                # systemd configuration
                wanted_by = "multi-user.target" if start_type == "auto" else ""
                
                # Make sure log_dir and env_file are absolute for Linux
                abs_log_dir = log_dir if log_dir.startswith("/") else f"/var/log/{name}"
                abs_env_file = env_file if env_file.startswith("/") else f"/etc/{name}/.env"
                
                service_content = f"""[Unit]
Description={desc}
After=network-online.target mysql.service postgresql.service
Wants=network-online.target

[Service]
Type=simple
User={os_user}
Group={os_group_or_pass}
WorkingDirectory={root_dir}
EnvironmentFile={abs_env_file}
"""
                if str(startup_delay).strip() and str(startup_delay).strip() != "0":
                    service_content += f"ExecStartPre=/bin/sleep {startup_delay}\n"
                    
                service_content += f"""ExecStart={bin_path.replace('"', '')} {args}
Restart={restart_policy}
RestartSec={restart_sec}
TimeoutStopSec=30
StartLimitBurst=5
StartLimitIntervalSec=10
LimitNOFILE=65536
MemoryMax=2G
"""
                if hardening:
                    service_content += f"""
# Enterprise Security Hardening
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths={root_dir} {abs_log_dir}
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
"""

                service_content += "\n[Install]\n"
                if wanted_by:
                    service_content += f"WantedBy={wanted_by}\n"
                    
                service_file = root_dir / f"{name}.service"
                with open(service_file, "w", encoding="utf-8") as f:
                    f.write(service_content)
                    
                # Bash script to automate creation
                bash_content = f"""#!/bin/bash
# Auto-generated installer for {name}
set -e

echo "=== Installing {name} ==="

if ! id "{os_user}" &>/dev/null; then
    echo "Creating dedicated service user: {os_user}"
    useradd -r -s /usr/sbin/nologin {os_user}
else
    echo "User {os_user} already exists."
fi

echo "Creating Log and Environment Directories..."
mkdir -p {abs_log_dir}
mkdir -p $(dirname {abs_env_file})
touch {abs_env_file}

echo "Applying strict ownership to {os_user}:{os_group_or_pass}..."
chown -R {os_user}:{os_group_or_pass} {abs_log_dir}
chown -R {os_user}:{os_group_or_pass} {root_dir}
chown {os_user}:{os_group_or_pass} {abs_env_file}
chmod 600 {abs_env_file}

echo "Installing systemd service file..."
cp {name}.service /etc/systemd/system/
systemctl daemon-reload

"""
                if start_type == "auto":
                    bash_content += f"systemctl enable --now {name}\n"
                else:
                    bash_content += f"systemctl start {name}\n"
                    
                bash_content += f"\necho \"✅ Installation complete! Check logs using: journalctl -u {name} -f\""
                
                bash_file = root_dir / f"install_{name}.sh"
                with open(bash_file, "w", encoding="utf-8", newline="\n") as f:
                    f.write(bash_content)
                    
                instructions = f"Successfully generated Linux configs at:\n1. {service_file}\n2. {bash_file}\n\n"
                instructions += f"To execute the fully automated deployment, simply run:\nsudo bash install_{name}.sh"
                
                return True, instructions
                
            return False, "Unknown Target OS"
            
        except Exception as e:
            logger.exception("Failed to generate service installer script.")
            return False, f"Generation failed: {str(e)}"
