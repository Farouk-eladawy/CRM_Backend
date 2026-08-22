import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getColors, spacing, typography, formatCurrency } from '@itour/shared';

interface EarningsSummaryProps {
  totalEarnings: number;
  completedCount: number;
  dateFrom: string;
  dateTo: string;
}

export function EarningsSummary({ totalEarnings, completedCount, dateFrom, dateTo }: EarningsSummaryProps) {
  const colors = getColors();

  return (
    <View style={[styles.container, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <Text style={[typography.caption, { color: colors.mutedForeground }]}>
        {dateFrom} - {dateTo}
      </Text>
      <Text style={[typography.h3, { color: colors.foreground, marginTop: spacing[1] }]}>
        {formatCurrency(totalEarnings, 'EGP')}
      </Text>
      <Text style={[typography.caption, { color: colors.mutedForeground }]}>
        {completedCount} completed {completedCount === 1 ? 'job' : 'jobs'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    padding: spacing[4],
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
    borderRadius: 12,
    borderWidth: 1,
  },
});
