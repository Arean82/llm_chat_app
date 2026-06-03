#!/bin/bash
# build_mac.sh - macOS PKG Installer Pipeline

APP_NAME="Synora Studio"
BUNDLE_NAME="$APP_NAME.app"
VERSION="9.0.0"
IDENTIFIER="com.arean82.synorastudio"
OUTPUT_PKG="LLM_Chat_App_Installer.pkg"

echo "Building macOS .pkg for $APP_NAME v$VERSION..."
rm -f "$OUTPUT_PKG"

# Compile first
echo "Compiling mac app bundle..."
pyinstaller LLM_Chat_App_mac.spec --noconfirm

if [ ! -d "dist/$BUNDLE_NAME" ]; then
    echo "Error: $BUNDLE_NAME not found in dist/. macOS build failed."
    exit 1
fi

pkgbuild --root "dist/$BUNDLE_NAME" \
         --identifier "$IDENTIFIER" \
         --version "$VERSION" \
         --install-location "/Applications/$BUNDLE_NAME" \
         "$OUTPUT_PKG"

echo "✅ macOS Installer created: $OUTPUT_PKG"
