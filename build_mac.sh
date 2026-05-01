#!/bin/bash
# build_mac.sh - Automates the creation of a macOS .pkg installer

APP_NAME="LLM Chat App"
BUNDLE_NAME="$APP_NAME.app"
VERSION="4.0.0"
IDENTIFIER="com.arean82.llmchatapp"
OUTPUT_PKG="LLM_Chat_App_Installer.pkg"

echo "Building macOS .pkg for $APP_NAME v$VERSION..."

# 1. Clean up old builds
rm -f "$OUTPUT_PKG"

# 2. Check if the .app bundle exists
if [ ! -d "dist/$BUNDLE_NAME" ]; then
    echo "Error: $BUNDLE_NAME not found in dist/. Run 'pyinstaller LLM_Chat_App_onedir.spec' first."
    exit 1
fi

# 3. Create the PKG installer
# --root: Path to the .app bundle
# --identifier: Your app's unique bundle ID
# --install-location: Where the app will be installed (standard is /Applications)
pkgbuild --root "dist/$BUNDLE_NAME" \
         --identifier "$IDENTIFIER" \
         --version "$VERSION" \
         --install-location "/Applications/$BUNDLE_NAME" \
         "$OUTPUT_PKG"

echo "------------------------------------------------"
echo "DONE! macOS Installer created: $OUTPUT_PKG"
echo "Note: This package works on both Intel and Apple Silicon (M1/M2/M3/M4)."
echo "------------------------------------------------"
