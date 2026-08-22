# iTour Mobile -- Environment Setup & CI/CD Guide

This document covers local development setup, Firebase and Stripe configuration,
build procedures, CI/CD pipelines, and troubleshooting for the iTour React Native
monorepo.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Getting Started](#2-getting-started)
3. [Firebase Setup](#3-firebase-setup)
4. [Stripe Setup (Guest App)](#4-stripe-setup-guest-app)
5. [Running Apps](#5-running-apps)
6. [Building for Production](#6-building-for-production)
7. [Fastlane](#7-fastlane)
8. [CI/CD Pipelines](#8-cicd-pipelines)
9. [CI/CD Secrets Reference](#9-cicd-secrets-reference)
10. [API Configuration](#10-api-configuration)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

Install the following before proceeding:

| Tool              | Version   | Notes                                          |
|-------------------|-----------|-------------------------------------------------|
| Node.js           | 20+       | Use nvm for version management                  |
| Yarn              | 1.22+     | Classic Yarn (v1) -- the workspace config uses it|
| Android Studio    | Latest    | Install Android SDK 34, build-tools, NDK         |
| Xcode             | 15+       | macOS only; includes iOS Simulator               |
| CocoaPods         | 1.14+     | `sudo gem install cocoapods`                     |
| Ruby              | 3.0+      | Required for Fastlane and CocoaPods              |
| Bundler           | 2.0+      | `gem install bundler`                            |
| Java (JDK)        | 17        | Temurin recommended; required for Gradle         |
| Fastlane          | Latest    | `gem install fastlane` or use Bundler            |

### Android Studio Setup

1. Open Android Studio and go to **SDK Manager**.
2. Install **Android SDK Platform 34** (API level 34).
3. Install **Android SDK Build-Tools 34.0.0**.
4. Under SDK Tools, install **Android NDK** and **CMake**.
5. Set the `ANDROID_HOME` environment variable:
   ```bash
   export ANDROID_HOME=$HOME/Android/Sdk       # Linux
   export ANDROID_HOME=$HOME/Library/Android/sdk # macOS
   export PATH=$PATH:$ANDROID_HOME/emulator
   export PATH=$PATH:$ANDROID_HOME/platform-tools
   ```

### Xcode Setup (macOS only)

1. Install Xcode from the Mac App Store.
2. Open Xcode and accept the license agreement.
3. Install command-line tools: `xcode-select --install`
4. Verify: `xcodebuild -version`

---

## 2. Getting Started

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd iTourTT/mobile
yarn install
```

The monorepo uses Yarn Workspaces with this structure:

```
mobile/
  packages/
    shared/       # Shared utilities, API clients, hooks, types, i18n
    ui/           # Shared UI component library
  apps/
    driver/       # iTour Driver app
    rep/          # iTour Rep app
    supplier/     # iTour Supplier app
    guest/        # iTour Booking (guest transfer) app
```

### Verifying Your Setup

Run the following to verify everything is configured:

```bash
yarn typecheck       # TypeScript compilation check
yarn lint            # ESLint across all packages and apps
yarn test            # Run Jest test suites
```

---

## 3. Firebase Setup

Firebase provides push notifications and authentication across all apps
except the guest app.

### 3.1 Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/).
2. Create a new project named `iTour Transport`.
3. Enable **Cloud Messaging** and **Authentication** (if applicable).

### 3.2 Add Android Apps

Register the following Android apps in Firebase:

| App       | Package Name        |
|-----------|---------------------|
| Driver    | `com.itour.driver`  |
| Rep       | `com.itour.rep`     |
| Supplier  | `com.itour.supplier`|

For each:

1. Click **Add App** > **Android**.
2. Enter the package name.
3. Download the `google-services.json` file.
4. Place it in the corresponding app directory:
   ```
   mobile/apps/driver/android/app/google-services.json
   mobile/apps/rep/android/app/google-services.json
   mobile/apps/supplier/android/app/google-services.json
   ```

### 3.3 Add iOS Apps

Register the following iOS apps:

| App       | Bundle ID            |
|-----------|----------------------|
| Driver    | `com.itour.driver`   |
| Rep       | `com.itour.rep`      |
| Supplier  | `com.itour.supplier` |

For each:

1. Click **Add App** > **iOS**.
2. Enter the bundle ID.
3. Download the `GoogleService-Info.plist` file.
4. Place it in the corresponding iOS project directory:
   ```
   mobile/apps/driver/ios/iTourDriver/GoogleService-Info.plist
   mobile/apps/rep/ios/iTourRep/GoogleService-Info.plist
   mobile/apps/supplier/ios/iTourSupplier/GoogleService-Info.plist
   ```

### 3.4 Firebase Admin (Backend)

1. In the Firebase Console, go to **Project Settings** > **Service Accounts**.
2. Click **Generate New Private Key** to download a JSON file.
3. On the backend server, set the environment variable:
   ```bash
   export FIREBASE_SERVICE_ACCOUNT=$(cat path/to/service-account.json)
   ```
   Or provide the file path:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   ```

> **Important**: Never commit Firebase service account JSON files to version
> control. Add them to `.gitignore`.

---

## 4. Stripe Setup (Guest App)

The guest booking app uses Stripe for payment processing.

### 4.1 Create a Stripe Account

1. Sign up at [Stripe Dashboard](https://dashboard.stripe.com/).
2. Complete business verification.

### 4.2 Get API Keys

1. In the Stripe Dashboard, go to **Developers** > **API keys**.
2. Copy the **Publishable key** (`pk_test_...` for test mode).
3. Copy the **Secret key** (`sk_test_...` for backend use only).

### 4.3 Configure in Guest App

Create or update the `.env` file at `mobile/`:

```bash
cp .env.example .env
```

Edit `.env` and set:

```
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
```

The secret key must be configured on the backend server only, never in the
mobile app.

### 4.4 Testing Payments

Use Stripe's test card numbers:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- 3D Secure: `4000 0027 6000 3184`

---

## 5. Running Apps

### Start Metro Bundler

The Metro bundler starts automatically when you run any app. To start it
manually:

```bash
cd apps/driver && npx react-native start
```

### Android

From the `mobile/` root:

```bash
yarn driver:android
yarn rep:android
yarn supplier:android
yarn guest:android
```

Make sure an Android emulator is running or a physical device is connected
(verify with `adb devices`).

### iOS (macOS only)

First, install CocoaPods dependencies for the target app:

```bash
cd apps/driver/ios && pod install && cd ../../..
```

Then run:

```bash
yarn driver:ios
yarn rep:ios
yarn supplier:ios
yarn guest:ios
```

To target a specific simulator:

```bash
cd apps/driver && npx react-native run-ios --simulator="iPhone 15 Pro"
```

---

## 6. Building for Production

### 6.1 Android Keystore Generation

Generate a release signing keystore (one per app or shared):

```bash
keytool -genkeypair \
  -v \
  -storetype PKCS12 \
  -keystore release.keystore \
  -alias itour-key \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

Place the keystore at:

```
mobile/apps/<app>/android/app/release.keystore
```

Configure signing in `android/app/build.gradle`:

```groovy
android {
    signingConfigs {
        release {
            storeFile file('release.keystore')
            storePassword System.getenv("KEYSTORE_PASSWORD") ?: ''
            keyAlias System.getenv("KEY_ALIAS") ?: 'itour-key'
            keyPassword System.getenv("KEY_PASSWORD") ?: ''
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

Build a release APK:

```bash
yarn build:android:driver    # or :rep, :supplier, :guest
```

Build a release AAB (for Play Store):

```bash
cd apps/driver/android && ./gradlew bundleRelease
```

### 6.2 iOS Certificates & Provisioning Profiles

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/).
2. In Xcode, go to **Signing & Capabilities** and sign in with your Apple ID.
3. Create **Distribution Certificates** in the Apple Developer portal.
4. Create **App Store Provisioning Profiles** for each bundle ID:
   - `com.itour.driver`
   - `com.itour.rep`
   - `com.itour.supplier`
   - `com.itour.guest`
5. Download and install the profiles in Xcode.

Build an archive:

```bash
cd apps/driver/ios
xcodebuild archive \
  -workspace iTourDriver.xcworkspace \
  -scheme iTourDriver \
  -configuration Release \
  -archivePath build/iTourDriver.xcarchive
```

Export IPA:

```bash
xcodebuild -exportArchive \
  -archivePath build/iTourDriver.xcarchive \
  -exportPath build/ipa \
  -exportOptionsPlist ExportOptions.plist
```

---

## 7. Fastlane

Each app has a `fastlane/` directory with a `Fastfile` and `Appfile`.

### Available Lanes

**Android:**
- `fastlane android build_debug` -- Build a debug APK
- `fastlane android build_release` -- Build a release APK
- `fastlane android deploy track:internal` -- Build AAB and upload to Play Store

**iOS:**
- `fastlane ios build_debug` -- Build for development testing
- `fastlane ios deploy` -- Build, archive, and upload to TestFlight

### Running Fastlane

Navigate to the app directory first:

```bash
cd apps/driver
fastlane android build_release
fastlane ios deploy
```

### Configuration

Edit `fastlane/Appfile` in each app to set:
- `json_key_file` -- Path to your Google Play service account JSON
- `apple_id` -- Your Apple ID email
- `team_id` -- Your App Store Connect Team ID

---

## 8. CI/CD Pipelines

Two GitHub Actions workflows are configured at `.github/workflows/`:

### mobile-ci.yml (Continuous Integration)

**Triggers**: Push to `main` or `develop`, PRs targeting `main` -- only when
files under `mobile/` change.

**Jobs**:

1. **Lint & Typecheck** -- Runs `yarn typecheck` and `yarn lint` on Ubuntu.
2. **Tests** -- Runs `yarn test:ci` with coverage report upload.
3. **Build Android** -- Matrix build for all 4 apps (`driver`, `rep`,
   `supplier`, `guest`). Produces APK artifacts.
4. **Build iOS** -- Matrix build for all 4 apps on macOS. Builds against
   iOS Simulator (no code signing required).

Android and iOS builds only run after lint/typecheck and tests pass.

### mobile-release.yml (Release / Deployment)

**Trigger**: Manual dispatch (`workflow_dispatch`) only.

**Inputs**:
- `app` -- Which app to release (driver, rep, supplier, guest)
- `platform` -- android, ios, or both
- `track` -- internal, beta, or production

**Android Release**:
1. Decodes the signing keystore from a base64 secret.
2. Builds a release AAB.
3. Uploads to Google Play Store on the selected track.

**iOS Release**:
1. Installs CocoaPods.
2. Builds and archives using the iOS build action.
3. Uploads the IPA to TestFlight.

---

## 9. CI/CD Secrets Reference

The following secrets must be configured in GitHub repository settings
(**Settings > Secrets and variables > Actions**):

### Android Secrets

| Secret Name                  | Description                                              |
|------------------------------|----------------------------------------------------------|
| `ANDROID_KEYSTORE_BASE64`    | Base64-encoded release keystore file                     |
| `KEYSTORE_PASSWORD`          | Password for the keystore                                |
| `KEY_ALIAS`                  | Alias of the signing key inside the keystore             |
| `KEY_PASSWORD`               | Password for the signing key                             |
| `GOOGLE_PLAY_SERVICE_ACCOUNT`| Google Play service account JSON (plain text)            |

To encode your keystore:

```bash
base64 -w 0 release.keystore > keystore-base64.txt
```

### iOS Secrets

| Secret Name                         | Description                                        |
|-------------------------------------|----------------------------------------------------|
| `IOS_P12_BASE64`                    | Base64-encoded .p12 distribution certificate       |
| `IOS_MOBILEPROVISION_BASE64`        | Base64-encoded .mobileprovision file               |
| `IOS_CERTIFICATE_PASSWORD`          | Password for the .p12 certificate                  |
| `APP_STORE_CONNECT_ISSUER_ID`       | App Store Connect API issuer ID                    |
| `APP_STORE_CONNECT_KEY_ID`          | App Store Connect API key ID                       |
| `APP_STORE_CONNECT_PRIVATE_KEY`     | App Store Connect API private key (.p8 contents)   |

To encode your certificate:

```bash
base64 -w 0 certificate.p12 > p12-base64.txt
base64 -w 0 profile.mobileprovision > mobileprovision-base64.txt
```

### Generating App Store Connect API Key

1. Go to [App Store Connect > Users and Access > Keys](https://appstoreconnect.apple.com/access/api).
2. Click the **+** button to create a new key.
3. Set role to **App Manager** or **Admin**.
4. Download the `.p8` file (only available once).
5. Note the **Key ID** and **Issuer ID** from the page.

---

## 10. API Configuration

### Environment Variables

Copy the example environment file and fill in values:

```bash
cp .env.example .env
```

| Variable                | Description                       | Example                             |
|-------------------------|-----------------------------------|-------------------------------------|
| `API_BASE_URL`          | Backend API base URL              | `https://api.itour.example.com`     |
| `STRIPE_PUBLISHABLE_KEY`| Stripe publishable key (guest)   | `pk_test_xxx`                       |

### Per-Environment Configuration

For different environments (development, staging, production), you can
create environment-specific files:

```
.env                # Default / development
.env.staging        # Staging environment
.env.production     # Production environment
```

Access environment variables in the app through the shared package's
configuration module. The API client in `packages/shared/src/api/` reads
`API_BASE_URL` to construct request URLs.

### Backend URL Requirements

The backend must expose the following base paths:

- `/api/auth/*` -- Authentication (login, refresh, logout)
- `/api/jobs/*` -- Traffic job management
- `/api/dispatch/*` -- Dispatch operations
- `/api/drivers/*` -- Driver data
- `/api/vehicles/*` -- Vehicle data
- `/api/locations/*` -- Location tree
- `/api/notifications/*` -- Push notification registration

---

## 11. Troubleshooting

### Metro Bundler

**Problem**: Metro bundler fails to start or shows port conflict.

```bash
# Kill existing Metro process
npx react-native start --reset-cache
# Or kill the process on port 8081
lsof -ti:8081 | xargs kill -9
```

**Problem**: Module not found errors after installing new packages.

```bash
# Clear Metro cache
cd mobile
yarn start --reset-cache
# If that fails, clear watchman
watchman watch-del-all
```

### Android Build Issues

**Problem**: `SDK location not found`.

```bash
# Create local.properties in the android directory
echo "sdk.dir=$ANDROID_HOME" > apps/driver/android/local.properties
```

**Problem**: Gradle build fails with memory errors.

```bash
# Increase Gradle memory in gradle.properties
echo "org.gradle.jvmargs=-Xmx4096m" >> apps/driver/android/gradle.properties
```

**Problem**: `Unable to load script from assets`.

```bash
# Create assets directory and bundle manually
mkdir -p apps/driver/android/app/src/main/assets
cd apps/driver
npx react-native bundle \
  --platform android \
  --dev false \
  --entry-file index.js \
  --bundle-output android/app/src/main/assets/index.android.bundle \
  --assets-dest android/app/src/main/res
```

### iOS Build Issues

**Problem**: CocoaPods install fails.

```bash
cd apps/driver/ios
pod deintegrate
pod cache clean --all
pod install --repo-update
```

**Problem**: Xcode build fails with signing errors.

- Open the `.xcworkspace` file in Xcode (not `.xcodeproj`).
- Go to **Signing & Capabilities**.
- Select your development team.
- Ensure the bundle identifier matches your provisioning profile.

**Problem**: `'React/RCTBridgeModule.h' file not found`.

```bash
cd apps/driver/ios
pod deintegrate && pod install
# Then clean Xcode build folder: Product > Clean Build Folder (Cmd+Shift+K)
```

### Firebase Connection Issues

**Problem**: Firebase initialization fails on Android.

- Verify `google-services.json` is in `android/app/` (not `android/`).
- Verify the package name in `google-services.json` matches `build.gradle`.
- Run `./gradlew clean` and rebuild.

**Problem**: Firebase initialization fails on iOS.

- Verify `GoogleService-Info.plist` is added to the Xcode project
  (not just the filesystem -- it must appear in the Xcode project navigator).
- Check that the bundle ID in `GoogleService-Info.plist` matches the target.

### Yarn Workspace Issues

**Problem**: Package not found errors for `@itour/shared` or `@itour/ui`.

```bash
# Ensure workspaces are linked
cd mobile
yarn install
# Verify workspace resolution
yarn workspaces info
```

**Problem**: Duplicate React versions.

Add resolutions to the root `package.json`:

```json
{
  "resolutions": {
    "react": "^19.0.0",
    "react-native": "^0.76.0"
  }
}
```

### General

**Problem**: Stale build cache causing unexpected behavior.

```bash
# Full clean (run from mobile/ root)
watchman watch-del-all 2>/dev/null
rm -rf node_modules
yarn install
cd apps/driver/android && ./gradlew clean && cd ../../..
cd apps/driver/ios && pod deintegrate && pod install && cd ../../..
```
