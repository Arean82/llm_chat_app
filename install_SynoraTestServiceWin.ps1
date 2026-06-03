<#
.SYNOPSIS
Auto-generated PowerShell Installer for SynoraTestServiceWin
Uses NSSM (Non-Sucking Service Manager) to securely wrap the application.
#>

$ErrorActionPreference = "Stop"

# 1. Require Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Please run this script as Administrator."
    Pause
    exit
}

Write-Host "=== Installing Windows Service: SynoraTestServiceWin ==="

$AppDir = "c:\Users\user\OneDrive\Desktop\python\llm_chat_app"
$LogDir = "logs"
$EnvFile = ".env"
$SvcUser = "root"
$SvcPass = "root"

# 2. NSSM Auto-Download
$NssmExe = Join-Path $AppDir "nssm.exe"
if (-Not (Test-Path $NssmExe)) {
    Write-Host "NSSM not found. Downloading the latest secure version..."
    $Url = "https://nssm.cc/release/nssm-2.24.zip"
    $ZipPath = Join-Path $AppDir "nssm.zip"
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath $AppDir -Force
    Copy-Item -Path (Join-Path $AppDir "nssm-2.24\win64\nssm.exe") -Destination $AppDir
    Remove-Item $ZipPath
    Remove-Item (Join-Path $AppDir "nssm-2.24") -Recurse
    Write-Host "NSSM downloaded successfully."
} else {
    Write-Host "NSSM executable found. (Update available? Checking manually is recommended)."
}

# 3. Create Dedicated User
if (-Not (Get-LocalUser -Name $SvcUser -ErrorAction SilentlyContinue)) {
    Write-Host "Creating dedicated service user: $SvcUser"
    $SecurePass = ConvertTo-SecureString $SvcPass -AsPlainText -Force
    New-LocalUser -Name $SvcUser -Password $SecurePass -PasswordNeverExpires -Description "Service Account for SynoraTestServiceWin"
} else {
    Write-Host "User $SvcUser already exists."
}

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
if (-Not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir }
icacls "$LogDir" /grant "$($SvcUser):(OI)(CI)F" /T /C /Q
icacls "$AppDir" /grant "$($SvcUser):(OI)(CI)F" /T /C /Q

# 6. Install via NSSM
Write-Host "Configuring service via NSSM..."
# Remove if exists
& $NssmExe stop SynoraTestServiceWin
& $NssmExe remove SynoraTestServiceWin confirm

& $NssmExe install SynoraTestServiceWin "python" "c:\Users\user\OneDrive\Desktop\python\llm_chat_app\main.py" --headless
& $NssmExe set SynoraTestServiceWin AppDirectory "$AppDir"
& $NssmExe set SynoraTestServiceWin Description "Synora Backend Service Test Description"
& $NssmExe set SynoraTestServiceWin Start $start_nssm

# Logging
& $NssmExe set SynoraTestServiceWin AppStdout "$LogDir\service.log"
& $NssmExe set SynoraTestServiceWin AppStderr "$LogDir\service_error.log"
& $NssmExe set SynoraTestServiceWin AppStdoutCreationDisposition 4
& $NssmExe set SynoraTestServiceWin AppStderrCreationDisposition 4

# Environment
if (Test-Path $EnvFile) {
    $envLines = Get-Content $EnvFile | Where-Object { $_ -match "=" }
    & $NssmExe set SynoraTestServiceWin AppEnvironmentExtra $envLines
}

# Run As User
& $NssmExe set SynoraTestServiceWin ObjectName ".\$SvcUser" "$SvcPass"

# Restart Recovery
& $NssmExe set SynoraTestServiceWin AppExit Default Restart
& $NssmExe set SynoraTestServiceWin AppThrottle 5000

Write-Host "Starting SynoraTestServiceWin..."
& $NssmExe start SynoraTestServiceWin

Write-Host "✅ Installation complete! Use Windows Services (services.msc) to view."
Pause
