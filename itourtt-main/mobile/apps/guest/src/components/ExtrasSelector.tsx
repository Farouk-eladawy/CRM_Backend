import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { spacing, borderRadius, typography } from '@itour/shared';
import type { BookingExtras } from '@itour/shared';

const BLUE_PRIMARY = '#1D4ED8';

interface ExtrasSelectorProps {
  extras: BookingExtras;
  onChangeExtra: (key: keyof BookingExtras, value: number) => void;
}

interface StepperRowProps {
  label: string;
  description: string;
  value: number;
  onIncrement: () => void;
  onDecrement: () => void;
}

function StepperRow({ label, description, value, onIncrement, onDecrement }: StepperRowProps) {
  return (
    <View style={styles.row}>
      <View style={styles.labelContainer}>
        <Text style={[typography.bodyMedium, { color: '#09090B' }]}>{label}</Text>
        <Text style={[typography.caption, { color: '#71717A' }]}>{description}</Text>
      </View>
      <View style={styles.stepper}>
        <TouchableOpacity
          style={[styles.stepperButton, value === 0 && styles.stepperDisabled]}
          onPress={onDecrement}
          disabled={value === 0}
        >
          <Text style={[styles.stepperText, value === 0 && { color: '#D4D4D8' }]}>-</Text>
        </TouchableOpacity>
        <Text style={[typography.bodyMedium, styles.stepperValue]}>{value}</Text>
        <TouchableOpacity style={styles.stepperButton} onPress={onIncrement}>
          <Text style={styles.stepperText}>+</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export function ExtrasSelector({ extras, onChangeExtra }: ExtrasSelectorProps) {
  return (
    <View style={styles.container}>
      <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
        Extras
      </Text>

      <StepperRow
        label="Baby Seat"
        description="For infants up to 12 months"
        value={extras.babySeatQty}
        onIncrement={() => onChangeExtra('babySeatQty', extras.babySeatQty + 1)}
        onDecrement={() => onChangeExtra('babySeatQty', Math.max(0, extras.babySeatQty - 1))}
      />

      <StepperRow
        label="Booster Seat"
        description="For children 1-4 years"
        value={extras.boosterSeatQty}
        onIncrement={() => onChangeExtra('boosterSeatQty', extras.boosterSeatQty + 1)}
        onDecrement={() => onChangeExtra('boosterSeatQty', Math.max(0, extras.boosterSeatQty - 1))}
      />

      <StepperRow
        label="Wheelchair"
        description="Wheelchair accessible vehicle"
        value={extras.wheelChairQty}
        onIncrement={() => onChangeExtra('wheelChairQty', extras.wheelChairQty + 1)}
        onDecrement={() => onChangeExtra('wheelChairQty', Math.max(0, extras.wheelChairQty - 1))}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: spacing[4],
    padding: spacing[4],
    backgroundColor: '#F9FAFB',
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: '#E4E4E7',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: '#F4F4F5',
  },
  labelContainer: {
    flex: 1,
  },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepperButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: BLUE_PRIMARY,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperDisabled: {
    borderColor: '#D4D4D8',
  },
  stepperText: {
    fontSize: 20,
    fontWeight: '600',
    color: BLUE_PRIMARY,
    lineHeight: 22,
  },
  stepperValue: {
    minWidth: 32,
    textAlign: 'center',
    color: '#09090B',
  },
});
