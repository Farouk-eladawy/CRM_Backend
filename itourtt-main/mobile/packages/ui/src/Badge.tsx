import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { borderRadius, typography } from '@itour/shared';

interface BadgeProps {
  label: string;
  backgroundColor: string;
  textColor: string;
  borderColor?: string;
}

export function Badge({ label, backgroundColor, textColor, borderColor }: BadgeProps) {
  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor,
          borderColor: borderColor || backgroundColor,
        },
      ]}
    >
      <Text style={[typography.captionMedium, { color: textColor }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: borderRadius.full,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
});
