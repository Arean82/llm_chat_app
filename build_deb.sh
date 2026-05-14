#!/bin/bash
# build_deb.sh - Automates the creation of a Linux .deb package

APP_NAME="llmchatapp"
VERSION="6.1.0"
PACKAGE_DIR="build_deb_pkg"
BUILD_OUTPUT="dist/LLM_Chat_dir"

echo "Building .deb package for $APP_NAME v$VERSION..."

# 1. Clean up old build artifacts
rm -rf "$PACKAGE_DIR"
rm -f "${APP_NAME}_${VERSION}.deb"

# 2. Create directory structure
mkdir -p "$PACKAGE_DIR/usr/local/bin"
mkdir -p "$PACKAGE_DIR/usr/share/applications"
mkdir -p "$PACKAGE_DIR/usr/share/icons/hicolor/512x512/apps"
mkdir -p "$PACKAGE_DIR/DEBIAN"

# 3. Copy application files (built with pyinstaller LLM_Chat_App_onedir.spec)
if [ ! -d "$BUILD_OUTPUT" ]; then
    echo "Error: Build output not found at $BUILD_OUTPUT. Run pyinstaller first."
    exit 1
fi
cp -r "$BUILD_OUTPUT/"* "$PACKAGE_DIR/usr/local/bin/"

# 4. Copy Icon
if [ -f "resources/app_icon_linux.png" ]; then
    cp resources/app_icon_linux.png "$PACKAGE_DIR/usr/share/icons/hicolor/512x512/apps/$APP_NAME.png"
fi

# 5. Create Desktop Entry
cat > "$PACKAGE_DIR/usr/share/applications/$APP_NAME.desktop" << EOF
[Desktop Entry]
Name=LLM Chat App
Exec="/usr/local/bin/LLM Chat App"
Icon=$APP_NAME
Type=Application
Categories=Utility;
Terminal=false
Comment=Universal multi-ecosystem desktop client
EOF

# 6. Create CONTROL file (Package metadata)
cat > "$PACKAGE_DIR/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Arean Narrayan
Description: LLM Chat Application
 Universal multi-ecosystem desktop client with universal API server support.
EOF

# 7. Create PRERM script (Handles clean UNINSTALL/UPDATE)
# This script runs BEFORE the package is removed or upgraded.
cat > "$PACKAGE_DIR/DEBIAN/prerm" << EOF
#!/bin/bash
# Kill any running instances of the app (including API server) to prevent file locks
echo "Stopping any running instances of LLM Chat App..."
pkill -f "LLM Chat App" || true
exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/prerm"

# 8. Create POSTINST script (Handles post-install setup)
cat > "$PACKAGE_DIR/DEBIAN/postinst" << EOF
#!/bin/bash
# Ensure correct permissions
chmod +x "/usr/local/bin/LLM Chat App"
echo "LLM Chat App installed successfully. You can find it in your Applications menu."
exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/postinst"

# 9. Build the .deb package
dpkg-deb --build "$PACKAGE_DIR" "${APP_NAME}_${VERSION}.deb"

echo "------------------------------------------------"
echo "DONE! Package created: ${APP_NAME}_${VERSION}.deb"
echo "Install with: sudo dpkg -i ${APP_NAME}_${VERSION}.deb"
echo "Remove with:  sudo apt remove $APP_NAME"
echo "------------------------------------------------"
