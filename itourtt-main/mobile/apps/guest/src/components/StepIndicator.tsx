import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { spacing, typography } from '@itour/shared';

const BLUE_PRIMARY = '#1D4ED8';
const BLUE_LIGHT = '#DBEAFE';
const GREY_MUTED = '#D4D4D8';

const STEP_LABELS = ['Search', 'Vehicle', 'Details', 'Payment', 'Confirm'];

interface StepIndicatorProps {
  currentStep: number; // 1-based
  totalSteps?: number;
}

export function StepIndicator({ currentStep, totalSteps = 5 }: StepIndicatorProps) {
  return (
    <View style={styles.container}>
      {Array.from({ length: totalSteps }, (_, i) => {
        const step = i + 1;
        const isActive = step === currentStep;
        const isCompleted = step < currentStep;

        return (
          <View key={step} style={styles.stepWrapper}>
            <View style={styles.dotRow}>
              {i > 0 && (
                <View
                  style={[
                    styles.line,
                    { backgroundColor: isCompleted || isActive ? BLUE_PRIMARY : GREY_MUTED },
                  ]}
                />
              )}
              <View
                style={[
                  styles.dot,
                  {
                    backgroundColor: isCompleted
                      ? BLUE_PRIMARY
                      : isActive
                        ? BLUE_LIGHT
                        : GREY_MUTED,
                    borderColor: isActive || isCompleted ? BLUE_PRIMARY : GREY_MUTED,
                  },
                ]}
              >
                {isCompleted && <Text style={styles.checkmark}>{'✓'}</Text>}
                {isActive && <View style={styles.innerDot} />}
              </View>
              {i < totalSteps - 1 && (
                <View
                  style={[
                    styles.line,
                    { backgroundColor: isCompleted ? BLUE_PRIMARY : GREY_MUTED },
                  ]}
                />
              )}
            </View>
            <Text
              style={[
                typography.caption,
                {
                  color: isActive || isCompleted ? BLUE_PRIMARY : '#71717A',
                  marginTop: spacing[0.5],
                  textAlign: 'center',
                },
              ]}
            >
              {STEP_LABELS[i] ?? `Step ${step}`}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'center',
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    backgroundColor: '#FFFFFF',
  },
  stepWrapper: {
    alignItems: 'center',
    flex: 1,
  },
  dotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    justifyContent: 'center',
  },
  dot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  innerDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: BLUE_PRIMARY,
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  line: {
    flex: 1,
    height: 2,
  },
});
