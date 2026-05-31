#!/bin/bash
# build_all_plugins.sh - Synora Studio IDE Plugins Bundler (V2.0.0 RELEASE)

echo "============================================================"
echo "🚀 LLM CHAT APP - IDE PLUGINS BUNDLER (V2.0.0 RELEASE)"
echo "============================================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VSCODE_STATUS="❌ FAILED TO COMPILE OR PACKAGE"
VSCODE_LOCATION="N/A"
VSCODE_INSTALL="Please check the build output log above for details."

JETBRAINS_STATUS="❌ FAILED TO COMPILE OR PACKAGE"
JETBRAINS_LOCATION="N/A"
JETBRAINS_INSTALL="Please check the build output log above for details."

# ----------------------------------------------------
# SECTION 1: VS Code Extension Package
# ----------------------------------------------------
echo ""
echo "[Step 1/2]: Packaging VS Code Extension..."
cd "$ROOT_DIR/vscode-llm-chat"

if [ ! -d "node_modules" ]; then
    echo "[VS Code]: Installing dependencies first..."
    npm install
fi

echo "[VS Code]: Compiling TypeScript..."
npm run compile

echo "[VS Code]: Packaging VSIX file..."
npx -y @vscode/vsce package

if [ -f "vscode-llm-chat-2.0.0.vsix" ]; then
    mkdir -p "$ROOT_DIR/extension"
    mv "vscode-llm-chat-2.0.0.vsix" "$ROOT_DIR/extension/" > /dev/null 2>&1
fi

if [ -f "$ROOT_DIR/extension/vscode-llm-chat-2.0.0.vsix" ]; then
    VSCODE_STATUS="✅ SUCCESSFULLY COMPILED AND BUNDLED"
    VSCODE_LOCATION="extension/vscode-llm-chat-2.0.0.vsix"
    VSCODE_INSTALL="Right-click the VSIX file in VS Code and select 'Install Extension VSIX'"
    echo "[VS Code]: Package copied to extension/vscode-llm-chat-2.0.0.vsix"
else
    echo "❌ Failed to package VS Code Extension."
fi

# ----------------------------------------------------
# SECTION 2: JetBrains IntelliJ Extension Package
# ----------------------------------------------------
echo ""
echo "[Step 2/2]: Packaging JetBrains IntelliJ Extension..."
cd "$ROOT_DIR/jetbrains-llm-chat"

echo "[JetBrains]: Compiling Kotlin and building plugin..."
chmod +x ./gradlew
./gradlew buildPlugin

if [ -f "build/distributions/jetbrains-llm-chat-2.0.0.zip" ]; then
    mkdir -p "$ROOT_DIR/extension"
    mv "build/distributions/jetbrains-llm-chat-2.0.0.zip" "$ROOT_DIR/extension/" > /dev/null 2>&1
fi

if [ -f "$ROOT_DIR/extension/jetbrains-llm-chat-2.0.0.zip" ]; then
    JETBRAINS_STATUS="✅ SUCCESSFULLY COMPILED AND BUNDLED"
    JETBRAINS_LOCATION="extension/jetbrains-llm-chat-2.0.0.zip"
    JETBRAINS_INSTALL="Open IDE - Settings - Plugins - [Gear Icon] - 'Install Plugin from Disk...' - select the zip file."
    echo "[JetBrains]: Package copied to extension/jetbrains-llm-chat-2.0.0.zip"
else
    echo "❌ Failed to package JetBrains Extension."
fi

# ----------------------------------------------------
# Completion
# ----------------------------------------------------
echo ""
echo "========================================================================"
echo "🎉               ALL IDE PLUGINS BUNDLED SUCCESSFULLY                  🎉"
echo "========================================================================"
echo ""
echo " [BUILD STATUS SUMMARY - VERSION 2.0.0]:"
echo ""
echo " 📦 VS Code Extension:"
echo "    Status:    $VSCODE_STATUS"
echo "    Location:  $VSCODE_LOCATION"
echo "    Install:   $VSCODE_INSTALL"
echo ""
echo " 📦 JetBrains IntelliJ Extension:"
echo "    Status:    $JETBRAINS_STATUS"
echo "    Location:  $JETBRAINS_LOCATION"
echo "    Install:   $JETBRAINS_INSTALL"
echo ""
echo "========================================================================"
echo " 🚀 Ready for dynamic multi-tenant cloud and local offline gateways!"
echo "========================================================================"
