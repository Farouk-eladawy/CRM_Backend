import { Platform } from 'react-native';
import { authApi } from '../api/endpoints/auth';

/**
 * Push notification service for mobile apps.
 * Uses @react-native-firebase/messaging under the hood.
 *
 * Each app should initialize this in their App.tsx after auth hydration.
 * The actual firebase messaging module is imported dynamically to avoid
 * requiring it in apps that don't use push (e.g., Guest app).
 */

let messagingModule: any = null;

/**
 * Set the firebase messaging module reference.
 * Call this from the app's entry point:
 *
 * ```
 * import messaging from '@react-native-firebase/messaging';
 * import { setFirebaseMessaging } from '@itour/shared';
 * setFirebaseMessaging(messaging);
 * ```
 */
export function setFirebaseMessaging(module: any) {
  messagingModule = module;
}

/**
 * Request notification permissions (required on iOS, optional on Android 13+).
 */
export async function requestNotificationPermission(): Promise<boolean> {
  if (!messagingModule) return false;

  const messaging = messagingModule();
  const authStatus = await messaging.requestPermission();
  const enabled =
    authStatus === 1 || // AUTHORIZED
    authStatus === 2;   // PROVISIONAL
  return enabled;
}

/**
 * Get the FCM device token and register it with the backend.
 */
export async function registerDeviceToken(): Promise<string | null> {
  if (!messagingModule) return null;

  try {
    const messaging = messagingModule();
    const token = await messaging.getToken();
    if (token) {
      const platform = Platform.OS as 'ios' | 'android';
      await authApi.registerDeviceToken(token, platform);
    }
    return token;
  } catch (error) {
    console.warn('Failed to register device token:', error);
    return null;
  }
}

/**
 * Unregister the device token from the backend (call on logout).
 */
export async function unregisterDeviceToken(): Promise<void> {
  if (!messagingModule) return;

  try {
    const messaging = messagingModule();
    const token = await messaging.getToken();
    if (token) {
      await authApi.unregisterDeviceToken(token);
    }
  } catch {
    // Ignore errors during logout cleanup
  }
}

/**
 * Listen for FCM token refresh events and re-register.
 * Returns a cleanup function.
 */
export function onTokenRefresh(): () => void {
  if (!messagingModule) return () => {};

  const messaging = messagingModule();
  return messaging.onTokenRefresh(async (newToken: string) => {
    try {
      const platform = Platform.OS as 'ios' | 'android';
      await authApi.registerDeviceToken(newToken, platform);
    } catch {
      // Ignore
    }
  });
}

/**
 * Set up foreground notification handler.
 * Returns a cleanup function.
 */
export function onForegroundMessage(
  handler: (notification: { title?: string; body?: string; data?: Record<string, string> }) => void,
): () => void {
  if (!messagingModule) return () => {};

  const messaging = messagingModule();
  return messaging.onMessage(async (remoteMessage: any) => {
    handler({
      title: remoteMessage.notification?.title,
      body: remoteMessage.notification?.body,
      data: remoteMessage.data,
    });
  });
}

/**
 * Handle notification tap when app is in background/killed state.
 * Call this in App.tsx to handle deep linking from push notifications.
 */
export function onNotificationOpened(
  handler: (data: Record<string, string>) => void,
): () => void {
  if (!messagingModule) return () => {};

  const messaging = messagingModule();

  // When app is in background and notification is tapped
  const unsubscribe = messaging.onNotificationOpenedApp((remoteMessage: any) => {
    if (remoteMessage.data) {
      handler(remoteMessage.data);
    }
  });

  // When app is killed and notification is tapped (check initial notification)
  messaging.getInitialNotification().then((remoteMessage: any) => {
    if (remoteMessage?.data) {
      handler(remoteMessage.data);
    }
  });

  return unsubscribe;
}

/**
 * Set background message handler.
 * Must be called outside of React components (e.g., in index.js).
 */
export function setBackgroundMessageHandler() {
  if (!messagingModule) return;

  const messaging = messagingModule();
  messaging.setBackgroundMessageHandler(async (_remoteMessage: any) => {
    // Background messages are handled by the OS notification tray.
    // No additional processing needed.
  });
}
