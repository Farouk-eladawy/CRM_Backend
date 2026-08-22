#!/bin/bash
# Generate app icons for all platforms from source PNGs
# Requires: ImageMagick (convert command)
#
# Usage: ./generate-icons.sh
#
# Place your 1024x1024 source icons in this directory:
#   driver-icon.png, rep-icon.png, supplier-icon.png, guest-icon.png

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MOBILE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Android icon sizes (mipmap)
declare -A ANDROID_SIZES=(
  [mdpi]=48
  [hdpi]=72
  [xhdpi]=96
  [xxhdpi]=144
  [xxxhdpi]=192
)

# iOS icon sizes
IOS_SIZES=(20 29 40 58 60 76 80 87 120 152 167 180 1024)

# App configs: app_dir, target_name, source_icon
declare -A APPS=(
  [driver]="iTourDriver:driver-icon.png"
  [rep]="iTourRep:rep-icon.png"
  [supplier]="iTourSupplier:supplier-icon.png"
  [guest]="iTourTransfer:guest-icon.png"
)

for app in "${!APPS[@]}"; do
  IFS=':' read -r target source <<< "${APPS[$app]}"

  if [ ! -f "$SCRIPT_DIR/$source" ]; then
    echo "WARNING: $source not found, skipping $app"
    continue
  fi

  echo "Generating icons for $app..."

  # Android
  for density in "${!ANDROID_SIZES[@]}"; do
    size=${ANDROID_SIZES[$density]}
    dir="$MOBILE_DIR/apps/$app/android/app/src/main/res/mipmap-$density"
    mkdir -p "$dir"
    convert "$SCRIPT_DIR/$source" -resize "${size}x${size}" "$dir/ic_launcher.png"
    convert "$SCRIPT_DIR/$source" -resize "${size}x${size}" \
      \( +clone -threshold -1 -negate -fill white -draw "roundrectangle 0,0,${size},${size},$((size/5)),$((size/5))" \) \
      -compose copy_opacity -composite "$dir/ic_launcher_round.png"
    echo "  Android $density: ${size}x${size}"
  done

  # iOS
  ios_dir="$MOBILE_DIR/apps/$app/ios/$target/Images.xcassets/AppIcon.appiconset"
  mkdir -p "$ios_dir"
  for size in "${IOS_SIZES[@]}"; do
    convert "$SCRIPT_DIR/$source" -resize "${size}x${size}" "$ios_dir/icon-${size}.png"
    echo "  iOS: ${size}x${size}"
  done

  # Generate Contents.json for iOS
  cat > "$ios_dir/Contents.json" << 'EOFIOS'
{
  "images": [
    { "filename": "icon-40.png", "idiom": "iphone", "scale": "2x", "size": "20x20" },
    { "filename": "icon-60.png", "idiom": "iphone", "scale": "3x", "size": "20x20" },
    { "filename": "icon-58.png", "idiom": "iphone", "scale": "2x", "size": "29x29" },
    { "filename": "icon-87.png", "idiom": "iphone", "scale": "3x", "size": "29x29" },
    { "filename": "icon-80.png", "idiom": "iphone", "scale": "2x", "size": "40x40" },
    { "filename": "icon-120.png", "idiom": "iphone", "scale": "3x", "size": "40x40" },
    { "filename": "icon-120.png", "idiom": "iphone", "scale": "2x", "size": "60x60" },
    { "filename": "icon-180.png", "idiom": "iphone", "scale": "3x", "size": "60x60" },
    { "filename": "icon-76.png", "idiom": "ipad", "scale": "1x", "size": "76x76" },
    { "filename": "icon-152.png", "idiom": "ipad", "scale": "2x", "size": "76x76" },
    { "filename": "icon-167.png", "idiom": "ipad", "scale": "2x", "size": "83.5x83.5" },
    { "filename": "icon-1024.png", "idiom": "ios-marketing", "scale": "1x", "size": "1024x1024" }
  ],
  "info": { "author": "xcode", "version": 1 }
}
EOFIOS

  echo "  Generated $app icons"
done

echo "Done! Place your 1024x1024 source PNGs in this directory and re-run."
