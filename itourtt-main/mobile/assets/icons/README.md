# App Icons

Place your source icon files here (1024x1024 PNG recommended).

## Required Files

- `driver-icon.png` - iTour Driver app icon (1024x1024)
- `rep-icon.png` - iTour Rep app icon (1024x1024)
- `supplier-icon.png` - iTour Supplier app icon (1024x1024)
- `guest-icon.png` - iTour Transfer app icon (1024x1024)

## Generating Platform-Specific Icons

### Android (Adaptive Icons)
Use Android Studio's Image Asset Studio or https://icon.kitchen:
1. Open Android Studio
2. Right-click `res` folder → New → Image Asset
3. Select your 1024x1024 source icon
4. Generate for all densities (mdpi, hdpi, xhdpi, xxhdpi, xxxhdpi)

Output directories per app:
```
apps/{app}/android/app/src/main/res/mipmap-mdpi/    (48x48)
apps/{app}/android/app/src/main/res/mipmap-hdpi/    (72x72)
apps/{app}/android/app/src/main/res/mipmap-xhdpi/   (96x96)
apps/{app}/android/app/src/main/res/mipmap-xxhdpi/  (144x144)
apps/{app}/android/app/src/main/res/mipmap-xxxhdpi/ (192x192)
```

### iOS (App Icon Set)
Use https://appicon.co or Xcode:
1. Upload 1024x1024 source icon
2. Download icon set
3. Place in `apps/{app}/ios/{Target}/Images.xcassets/AppIcon.appiconset/`

Required sizes:
- 40x40, 60x60 (iPhone @2x)
- 58x58, 87x87 (iPhone @3x)
- 80x80, 120x120 (iPhone @2x/@3x)
- 1024x1024 (App Store)

## Splash Screen

Place splash screen logo at:
- `splash-logo.png` (288x288, transparent background)

Use `npx react-native-bootsplash generate` to create platform assets.
