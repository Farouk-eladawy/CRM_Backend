import React from 'react';
import { View, StyleSheet } from 'react-native';
import { getColors, spacing, borderRadius } from '@itour/shared';
import { Skeleton } from './Skeleton';

export function SkeletonProfile() {
  const colors = getColors();
  return (
    <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <Skeleton width="60%" height={24} style={{ marginBottom: spacing[3] }} />
      <Skeleton width="40%" height={12} style={{ marginBottom: spacing[1] }} />
      <Skeleton width="70%" height={16} style={{ marginBottom: spacing[3] }} />
      <Skeleton width="40%" height={12} style={{ marginBottom: spacing[1] }} />
      <Skeleton width="50%" height={16} />
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
  },
});
