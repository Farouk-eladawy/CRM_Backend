import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNetwork, typography, spacing, useT } from '@itour/shared';

export function OfflineBar() {
  const { isConnected } = useNetwork();
  const t = useT();

  if (isConnected) return null;

  return (
    <View style={styles.bar}>
      <Text style={[typography.captionMedium, styles.text]}>{t('common.offline')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: '#EF4444',
    paddingVertical: spacing[1],
    alignItems: 'center',
  },
  text: {
    color: '#FFFFFF',
  },
});
