#!/bin/bash
# build_appimage.sh - Build an AppImage for Linux

APPDIR="LLMChatApp.AppDir"

# 1. Create folder structure
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/512x512/apps"

# 2. Copy PyInstaller output
cp -r "dist/LLM_Chat_dir/"* "$APPDIR/usr/bin/"

# 3. Create Linux Desktop Shortcut
cat << 'EOF' > "$APPDIR/LLMChatApp.desktop"
[Desktop Entry]
Name=Synora Studio
Exec=AppRun
Icon=app_icon
Type=Application
Categories=Utility;
EOF

# 4. Copy Icon
cp resources/app_icon_linux.png "$APPDIR/usr/share/icons/hicolor/512x512/apps/app_icon.png"
ln -s "$APPDIR/usr/share/icons/hicolor/512x512/apps/app_icon.png" "$APPDIR/app_icon.png"

# 5. Detect Architecture and Download AppImage tool
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    APPIMAGE_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-aarch64.AppImage"
else
    APPIMAGE_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
fi

wget -O appimagetool "$APPIMAGE_URL"
chmod +x appimagetool
./appimagetool "$APPDIR/"

echo "Linux AppImage created successfully!"
