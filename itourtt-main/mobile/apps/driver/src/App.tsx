import React, { useEffect, useState, useCallback } from 'react';
import { StatusBar, Alert } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import messaging from '@react-native-firebase/messaging';
import {
  useAuthStore,
  useThemeStore,
  useTheme,
  setOnAuthFailure,
  getColors,
  setFirebaseMessaging,
  requestNotificationPermission,
  registerDeviceToken,
  unregisterDeviceToken,
  onTokenRefresh,
  onForegroundMessage,
  onNotificationOpened,
} from '@itour/shared';
import { OfflineBar } from '@itour/ui';
import { RootNavigator } from './navigation/RootNavigator';

// Initialize Firebase messaging for push notifications
setFirebaseMessaging(messaging);

export function App() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [ready, setReady] = useState(false);
  const { isDark } = useTheme();
  const colors = getColors();
  const navigationRef = React.useRef<any>(null);

  useEffect(() => {
    setOnAuthFailure(() => {
      navigationRef.current?.reset({ index: 0, routes: [{ name: 'Login' }] });
    });

    Promise.all([hydrate(), useThemeStore.getState().hydrate()]).then(() => setReady(true));
  }, [hydrate]);

  // Push notification setup after authentication
  useEffect(() => {
    if (!isAuthenticated) return;

    let tokenRefreshCleanup: () => void;
    let foregroundCleanup: () => void;
    let openedCleanup: () => void;

    (async () => {
      await requestNotificationPermission();
      await registerDeviceToken();

      tokenRefreshCleanup = onTokenRefresh();

      foregroundCleanup = onForegroundMessage(({ title, body }) => {
        if (title || body) {
          Alert.alert(title || 'Notification', body || '');
        }
      });

      openedCleanup = onNotificationOpened((data) => {
        if (data.jobId) {
          navigationRef.current?.navigate('JobDetail', { jobId: data.jobId });
        }
      });
    })();

    return () => {
      tokenRefreshCleanup?.();
      foregroundCleanup?.();
      openedCleanup?.();
    };
  }, [isAuthenticated]);

  if (!ready) return null;

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} backgroundColor={colors.background} />
      <NavigationContainer ref={navigationRef}>
        <OfflineBar />
        <RootNavigator />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
