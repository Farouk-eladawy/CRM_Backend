import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { getColors, borderRadius, spacing, typography, useT } from '@itour/shared';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  const colors = getColors();
  const t = useT();

  return (
    <View style={[styles.container, { backgroundColor: colors.destructive + '15' }]}>
      <Text style={[typography.bodySm, { color: colors.destructive, flex: 1 }]}>{message}</Text>
      {onRetry && (
        <TouchableOpacity onPress={onRetry}>
          <Text style={[typography.bodySmMedium, { color: colors.destructive }]}>{t('common.retry')}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing[3],
    borderRadius: borderRadius.lg,
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
  },
});
