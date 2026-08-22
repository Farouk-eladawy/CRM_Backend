import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getColors, spacing, typography, type SupplierProfile } from '@itour/shared';
import { Card } from '@itour/ui';

interface FleetOverviewProps {
  profile: SupplierProfile;
}

export function FleetOverview({ profile }: FleetOverviewProps) {
  const colors = getColors();
  const vehicleCount = profile.vehicles?.length ?? 0;
  const driverCount = profile.drivers?.length ?? 0;

  return (
    <Card style={styles.card}>
      <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[3] }]}>
        Fleet Overview
      </Text>
      <View style={styles.row}>
        <View style={styles.item}>
          <Text style={[typography.h2, { color: colors.primary }]}>{vehicleCount}</Text>
          <Text style={[typography.caption, { color: colors.mutedForeground }]}>Vehicles</Text>
        </View>
        <View style={[styles.divider, { backgroundColor: colors.border }]} />
        <View style={styles.item}>
          <Text style={[typography.h2, { color: colors.primary }]}>{driverCount}</Text>
          <Text style={[typography.caption, { color: colors.mutedForeground }]}>Drivers</Text>
        </View>
      </View>

      {vehicleCount > 0 && (
        <View style={styles.vehicleList}>
          <Text style={[typography.caption, { color: colors.mutedForeground, marginBottom: spacing[1] }]}>
            Vehicle Types
          </Text>
          {profile.vehicles.map((vehicle) => (
            <View key={vehicle.id} style={styles.vehicleRow}>
              <Text style={[typography.bodySm, { color: colors.foreground }]}>
                {vehicle.plateNumber}
              </Text>
              <Text style={[typography.caption, { color: colors.mutedForeground }]}>
                {vehicle.vehicleType?.name}
              </Text>
            </View>
          ))}
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: spacing[4],
    marginTop: spacing[3],
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  item: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing[2],
  },
  divider: {
    width: 1,
    height: 40,
  },
  vehicleList: {
    marginTop: spacing[3],
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(0,0,0,0.1)',
    paddingTop: spacing[3],
  },
  vehicleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing[1],
  },
});
