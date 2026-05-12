#!/bin/bash
APPDIR="LLMChatApp.AppDir"

# 1. Create folder structure
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# 2. Copy PyInstaller output
cp -r "dist/LLM_Chat_dir/"* "$APPDIR/usr/bin/"

# 3. Create Linux Desktop Shortcut
cat << 'EOF' > "$APPDIR/LLMChatApp.desktop"
[Desktop Entry]
Name=LLM Chat App
Exec=AppRun
Icon=app_icon
Type=Application
Categories=Utility;
EOF

# 4. Copy Icon
cp resources/app_icon_linux.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/app_icon.png"
ln -s "$APPDIR/usr/share/icons/hicolor/256x256/apps/app_icon.png" "$APPDIR/app_icon.png"

# 5. Download AppImage tool and build
wget -O appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x appimagetool
./appimagetool "$APPDIR/"

echo "Linux AppImage created successfully!"