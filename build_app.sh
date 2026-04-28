#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python3.12 ]; then
  python3.12 -m venv .venv
fi

ln -sf python3.12 .venv/bin/python
ln -sf python3.12 .venv/bin/python3

APP_DIR="dist/mini-gpt-helper.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

rm -rf build dist
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

cat > "$CONTENTS_DIR/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>mini-gpt-helper</string>
    <key>CFBundleIdentifier</key>
    <string>local.daniil.mini-gpt-helper</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>mini-gpt-helper</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

pwd > "$RESOURCES_DIR/repo_root.txt"

clang \
  native_launcher.c \
  -o "$MACOS_DIR/mini-gpt-helper" \
  $(python3.12-config --includes) \
  $(python3.12-config --embed --ldflags)
