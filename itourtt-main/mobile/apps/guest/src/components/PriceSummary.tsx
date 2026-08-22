import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { spacing, borderRadius, typography } from '@itour/shared';

const BLUE_PRIMARY = '#1D4ED8';

interface PriceSummaryProps {
  price: number | null;
  currency: string;
  vehicleTypeName?: string;
  paxCount?: number;
  extras?: {
    babySeatQty: number;
    boosterSeatQty: number;
    wheelChairQty: number;
  };
  breakdown?: Record<string, unknown> | null;
}

export function PriceSummary({
  price,
  currency,
  vehicleTypeName,
  paxCount,
  extras,
  breakdown,
}: PriceSummaryProps) {
  if (price === null) return null;

  return (
    <View style={styles.container}>
      <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
        Price Summary
      </Text>

      {vehicleTypeName && (
        <View style={styles.row}>
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Vehicle</Text>
          <Text style={[typography.bodySmMedium, { color: '#09090B' }]}>{vehicleTypeName}</Text>
        </View>
      )}

      {paxCount !== undefined && (
        <View style={styles.row}>
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Passengers</Text>
          <Text style={[typography.bodySmMedium, { color: '#09090B' }]}>{paxCount}</Text>
        </View>
      )}

      {extras && extras.babySeatQty > 0 && (
        <View style={styles.row}>
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Baby Seat</Text>
          <Text style={[typography.bodySmMedium, { color: '#09090B' }]}>x{extras.babySeatQty}</Text>
        </View>
      )}

      {extras && extras.boosterSeatQty > 0 && (
        <View style={styles.row}>
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Booster Seat</Text>
          <Text style={[typography.bodySmMedium, { color: '#09090B' }]}>x{extras.boosterSeatQty}</Text>
        </View>
      )}

      {extras && extras.wheelChairQty > 0 && (
        <View style={styles.row}>
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Wheelchair</Text>
          <Text style={[typography.bodySmMedium, { color: '#09090B' }]}>x{extras.wheelChairQty}</Text>
        </View>
      )}

      {breakdown &&
        Object.entries(breakdown).map(([key, val]) => (
          <View key={key} style={styles.row}>
            <Text style={[typography.bodySm, { color: '#71717A' }]}>{key}</Text>
            <Text style={[typography.bodySmMedium, { color: '#09090B' }]}>{String(val)}</Text>
          </View>
        ))}

      <View style={[styles.row, styles.totalRow]}>
        <Text style={[typography.bodyMedium, { color: '#09090B' }]}>Total</Text>
        <Text style={[typography.h3, { color: BLUE_PRIMARY }]}>
          {currency} {price.toFixed(2)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing[4],
    backgroundColor: '#F9FAFB',
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: '#E4E4E7',
    marginTop: spacing[4],
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing[1.5],
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#E4E4E7',
    marginTop: spacing[2],
    paddingTop: spacing[3],
  },
});
