import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { getColors, typography, spacing } from '@itour/shared';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'small' | 'large';
  fullScreen?: boolean;
}

export function LoadingSpinner({ message, size = 'large', fullScreen = false }: LoadingSpinnerProps) {
  const colors = getColors();

  return (
    <View style={[styles.container, fullScreen && styles.fullScreen]}>
      <ActivityIndicator size={size} color={colors.primary} />
      {message && (
        <Text style={[typography.bodySm, { color: colors.mutedForeground, marginTop: spacing[2] }]}>
          {message}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  fullScreen: {
    flex: 1,
  },
});
