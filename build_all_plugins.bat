@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo 🚀 LLM CHAT APP - IDE PLUGINS BUNDLER (V2.0.0 RELEASE)
echo ============================================================

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

:: Initialize dynamic status variables
set VSCODE_STATUS=❌ FAILED TO COMPILE OR PACKAGE
set VSCODE_LOCATION=N/A
set VSCODE_INSTALL=Please check the build output log above for details.

set JETBRAINS_STATUS=❌ FAILED TO COMPILE OR PACKAGE
set JETBRAINS_LOCATION=N/A
set JETBRAINS_INSTALL=Please check the build output log above for details.

:: ----------------------------------------------------
:: SECTION 1: VS Code Extension Package
:: ----------------------------------------------------
echo.
echo [Step 1/2]: Packaging VS Code Extension...
cd "%ROOT_DIR%vscode-llm-chat"

if not exist "node_modules" (
    echo [VS Code]: Installing dependencies first...
    call npm install
)

echo [VS Code]: Compiling TypeScript...
call npm run compile

echo [VS Code]: Packaging VSIX file...
call npx -y @vscode/vsce package

if exist "vscode-llm-chat-2.0.0.vsix" (
    if not exist "%ROOT_DIR%extension" mkdir "%ROOT_DIR%extension"
    move /y "vscode-llm-chat-2.0.0.vsix" "%ROOT_DIR%extension\" >nul
)

if exist "%ROOT_DIR%extension\vscode-llm-chat-2.0.0.vsix" (
    set VSCODE_STATUS=✅ SUCCESSFULLY COMPILED AND BUNDLED
    set VSCODE_LOCATION=extension\vscode-llm-chat-2.0.0.vsix
    set VSCODE_INSTALL=Right-click the VSIX file in VS Code and select "Install Extension VSIX"
    echo [VS Code]: Package copied to extension\vscode-llm-chat-2.0.0.vsix
) else (
    echo ❌ Failed to package VS Code Extension.
)

:: ----------------------------------------------------
:: SECTION 2: JetBrains IntelliJ Extension Package
:: ----------------------------------------------------
echo.
echo [Step 2/2]: Packaging JetBrains IntelliJ Extension...
cd "%ROOT_DIR%jetbrains-llm-chat"

echo [JetBrains]: Compiling Kotlin and building plugin...
call gradlew.bat buildPlugin

if exist "build\distributions\jetbrains-llm-chat-2.0.0.zip" (
    if not exist "%ROOT_DIR%extension" mkdir "%ROOT_DIR%extension"
    move /y "build\distributions\jetbrains-llm-chat-2.0.0.zip" "%ROOT_DIR%extension\" >nul
)

if exist "%ROOT_DIR%extension\jetbrains-llm-chat-2.0.0.zip" (
    set JETBRAINS_STATUS=✅ SUCCESSFULLY COMPILED AND BUNDLED
    set JETBRAINS_LOCATION=extension\jetbrains-llm-chat-2.0.0.zip
    set JETBRAINS_INSTALL=Open IDE - Settings - Plugins - [Gear Icon] - "Install Plugin from Disk..." - select the zip file.
    echo [JetBrains]: Package copied to extension\jetbrains-llm-chat-2.0.0.zip
) else (
    echo ❌ Failed to package JetBrains Extension.
)

:: ----------------------------------------------------
:: Completion
:: ----------------------------------------------------
echo.
echo ========================================================================
echo 🎉               ALL IDE PLUGINS BUNDLED SUCCESSFULLY                  🎉
echo ========================================================================
echo.
echo  [BUILD STATUS SUMMARY - VERSION 2.0.0]:
echo.
echo  📦 VS Code Extension:
echo     Status:    !VSCODE_STATUS!
echo     Location:  !VSCODE_LOCATION!
echo     Install:   !VSCODE_INSTALL!
echo.
echo  📦 JetBrains IntelliJ Extension:
echo     Status:    !JETBRAINS_STATUS!
echo     Location:  !JETBRAINS_LOCATION!
echo     Install:   !JETBRAINS_INSTALL!
echo.
echo ========================================================================
echo  🚀 Ready for dynamic multi-tenant cloud and local offline gateways!
echo ========================================================================
pause
