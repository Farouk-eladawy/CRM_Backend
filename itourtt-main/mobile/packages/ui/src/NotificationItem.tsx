import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { getColors, spacing, typography, formatDate, type PortalNotification } from '@itour/shared';

interface NotificationItemProps {
  notification: PortalNotification;
  onPress?: () => void;
}

export function NotificationItem({ notification, onPress }: NotificationItemProps) {
  const colors = getColors();

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[
        styles.container,
        {
          backgroundColor: notification.isRead ? colors.card : colors.accent,
          borderColor: colors.border,
        },
      ]}
    >
      {!notification.isRead && <View style={styles.dot} />}
      <View style={styles.content}>
        <Text style={[typography.bodySmMedium, { color: colors.foreground }]}>
          {notification.title}
        </Text>
        <Text
          style={[typography.caption, { color: colors.mutedForeground, marginTop: spacing[0.5] }]}
          numberOfLines={2}
        >
          {notification.message}
        </Text>
        <Text style={[typography.caption, { color: colors.mutedForeground, marginTop: spacing[1] }]}>
          {formatDate(notification.createdAt)}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: spacing[4],
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3B82F6',
    marginTop: 6,
    marginRight: spacing[3],
  },
  content: {
    flex: 1,
  },
});
