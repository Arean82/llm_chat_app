#!/bin/bash
# build_deb.sh - Automates the creation of a Linux .deb package

APP_NAME="synorastudio"
VERSION="9.0.0"
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

# 3. Copy application files (built with pyinstaller)
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
Name=Synora Studio
Exec="/usr/local/bin/Synora Studio"
Icon=$APP_NAME
Type=Application
Categories=Utility;
Terminal=false
Comment=Universal multi-ecosystem desktop client
EOF

# 6. Create CONTROL file
cat > "$PACKAGE_DIR/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $(dpkg --print-architecture)
Maintainer: Arean Narrayan
Description: LLM Chat Application
 Universal multi-ecosystem desktop client with universal API server support.
EOF

# 7. Create PRERM script (Kills processes before uninstall)
cat > "$PACKAGE_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
echo "Stopping any running instances of Synora Studio..."
pkill -f "Synora Studio" || true
exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/prerm"

# 8. Create POSTRM script (Full Uninstall Data Purge)
cat > "$PACKAGE_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
if [ "$1" = "purge" ] || [ "$1" = "remove" ]; then
    echo "Purging all user data..."
    rm -rf "/usr/local/bin/Synora Studio*"
fi
exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/postrm"

# 9. Create POSTINST script
cat > "$PACKAGE_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
chmod +x "/usr/local/bin/Synora Studio"
echo "Synora Studio installed successfully. You can find it in your Applications menu."
exit 0
EOF
chmod 755 "$PACKAGE_DIR/DEBIAN/postinst"

# 10. Build the .deb package
dpkg-deb --build "$PACKAGE_DIR" "${APP_NAME}_${VERSION}.deb"

echo "------------------------------------------------"
echo "DONE! Package created: ${APP_NAME}_${VERSION}.deb"
echo "Install with: sudo dpkg -i ${APP_NAME}_${VERSION}.deb"
echo "Remove with:  sudo apt remove $APP_NAME"
echo "------------------------------------------------"
