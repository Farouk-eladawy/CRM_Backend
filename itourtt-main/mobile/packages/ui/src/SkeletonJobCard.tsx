import React from 'react';
import { View, StyleSheet } from 'react-native';
import { getColors, spacing, borderRadius } from '@itour/shared';
import { Skeleton } from './Skeleton';

export function SkeletonJobCard() {
  const colors = getColors();
  return (
    <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <View style={styles.header}>
        <Skeleton width={60} height={22} borderRadius={borderRadius.sm} />
        <Skeleton width={80} height={22} borderRadius={borderRadius.full} />
      </View>
      <Skeleton width="70%" height={16} style={{ marginTop: spacing[2] }} />
      <Skeleton width="50%" height={14} style={{ marginTop: spacing[2] }} />
      <View style={styles.footer}>
        <Skeleton width={40} height={14} />
        <Skeleton width={60} height={14} />
        <Skeleton width={50} height={14} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: spacing[4],
    marginTop: spacing[3],
    padding: spacing[4],
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    borderLeftWidth: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing[3],
  },
});
