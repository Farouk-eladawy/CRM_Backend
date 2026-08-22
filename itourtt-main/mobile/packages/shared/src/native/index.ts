// Phone
export { callPhone, openDialer } from './phone';

// WhatsApp
export { openWhatsApp, sendJobWhatsApp } from './whatsapp';

// Camera
export { takePhoto, pickPhoto, captureOrPick } from './camera';
export type { CapturedPhoto } from './camera';

// Location
export { getCurrentPosition, watchPosition, requestLocationPermission, getMapLink } from './location';
export type { GPSPosition } from './location';

// Push Notifications
export {
  setFirebaseMessaging,
  requestNotificationPermission,
  registerDeviceToken,
  unregisterDeviceToken,
  onTokenRefresh,
  onForegroundMessage,
  onNotificationOpened,
  setBackgroundMessageHandler,
} from './push-notifications';
