import React, { useEffect, useState } from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useThemeStore, useTheme, getColors } from '@itour/shared';
import { OfflineBar } from '@itour/ui';
import { RootNavigator } from './navigation/RootNavigator';

export function App() {
  const [ready, setReady] = useState(false);
  const { isDark } = useTheme();
  const colors = getColors();

  useEffect(() => {
    useThemeStore.getState().hydrate().then(() => setReady(true));
  }, []);

  if (!ready) return null;

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} backgroundColor={colors.background} />
      <NavigationContainer>
        <OfflineBar />
        <RootNavigator />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
