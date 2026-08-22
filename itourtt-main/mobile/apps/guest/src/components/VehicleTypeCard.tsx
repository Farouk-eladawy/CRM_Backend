import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { spacing, borderRadius, typography } from '@itour/shared';
import type { VehicleType } from '@itour/shared';

const BLUE_PRIMARY = '#1D4ED8';
const BLUE_LIGHT = '#EFF6FF';

interface VehicleTypeCardProps {
  vehicleType: VehicleType;
  price: number | null;
  currency: string;
  loading?: boolean;
  selected: boolean;
  onSelect: () => void;
}

export function VehicleTypeCard({
  vehicleType,
  price,
  currency,
  loading = false,
  selected,
  onSelect,
}: VehicleTypeCardProps) {
  return (
    <TouchableOpacity
      style={[
        styles.container,
        selected && styles.selected,
      ]}
      onPress={onSelect}
      activeOpacity={0.7}
    >
      <View style={styles.iconContainer}>
        <Text style={styles.iconText}>
          {vehicleType.seatCapacity <= 4 ? 'S' : vehicleType.seatCapacity <= 7 ? 'M' : 'L'}
        </Text>
      </View>

      <View style={styles.info}>
        <Text style={[typography.bodyMedium, { color: '#09090B' }]}>
          {vehicleType.name}
        </Text>
        <Text style={[typography.bodySm, { color: '#71717A' }]}>
          Up to {vehicleType.seatCapacity} passengers
        </Text>
      </View>

      <View style={styles.priceContainer}>
        {loading ? (
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Loading...</Text>
        ) : price !== null ? (
          <>
            <Text style={[typography.h4, { color: BLUE_PRIMARY }]}>
              {currency} {price.toFixed(2)}
            </Text>
          </>
        ) : (
          <Text style={[typography.bodySm, { color: '#71717A' }]}>--</Text>
        )}
      </View>

      {selected && (
        <View style={styles.checkContainer}>
          <View style={styles.checkCircle}>
            <Text style={styles.checkText}>{'✓'}</Text>
          </View>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing[4],
    borderWidth: 1,
    borderColor: '#E4E4E7',
    borderRadius: borderRadius.xl,
    backgroundColor: '#FFFFFF',
    marginBottom: spacing[3],
  },
  selected: {
    borderColor: BLUE_PRIMARY,
    backgroundColor: BLUE_LIGHT,
    borderWidth: 2,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.lg,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing[3],
  },
  iconText: {
    fontSize: 20,
    fontWeight: '700',
    color: BLUE_PRIMARY,
  },
  info: {
    flex: 1,
  },
  priceContainer: {
    alignItems: 'flex-end',
    marginLeft: spacing[2],
  },
  checkContainer: {
    marginLeft: spacing[2],
  },
  checkCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: BLUE_PRIMARY,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
});
