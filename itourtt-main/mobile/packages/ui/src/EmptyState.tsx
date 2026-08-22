import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getColors, typography, spacing } from '@itour/shared';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  message?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, message, action }: EmptyStateProps) {
  const colors = getColors();

  return (
    <View style={styles.container}>
      {icon && <View style={styles.icon}>{icon}</View>}
      <Text style={[typography.h4, { color: colors.foreground, textAlign: 'center' }]}>
        {title}
      </Text>
      {message && (
        <Text
          style={[
            typography.bodySm,
            { color: colors.mutedForeground, textAlign: 'center', marginTop: spacing[1] },
          ]}
        >
          {message}
        </Text>
      )}
      {action && <View style={styles.action}>{action}</View>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing[8],
  },
  icon: {
    marginBottom: spacing[4],
  },
  action: {
    marginTop: spacing[4],
  },
});
