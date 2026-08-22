import React, { useState, useEffect, useCallback } from 'react';
import { View, FlatList, StyleSheet } from 'react-native';
import {
  repPortalApi,
  getColors,
  spacing,
  useRefresh,
  useT,
  type PortalNotification,
} from '@itour/shared';
import { NotificationItem, EmptyState, LoadingSpinner, Button } from '@itour/ui';

export function NotificationsScreen() {
  const colors = getColors();
  const t = useT();
  const [notifications, setNotifications] = useState<PortalNotification[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      const { data } = await repPortalApi.getNotifications();
      const list = Array.isArray(data) ? data : (data as any)?.data ?? [];
      setNotifications(list);
    } catch {
      // handled silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const { refreshing, handleRefresh } = useRefresh(fetchNotifications);

  const handleMarkRead = async (id: string) => {
    try {
      await repPortalApi.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, isRead: true } : n)),
      );
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await repPortalApi.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
    } catch {
      // ignore
    }
  };

  const hasUnread = notifications.some((n) => !n.isRead);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {hasUnread && (
        <View style={styles.markAllRow}>
          <Button
            title={t('notifications.markAllRead')}
            variant="ghost"
            size="sm"
            onPress={handleMarkAllRead}
          />
        </View>
      )}

      {loading && !refreshing ? (
        <LoadingSpinner fullScreen />
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <NotificationItem
              notification={item}
              onPress={() => !item.isRead && handleMarkRead(item.id)}
            />
          )}
          refreshing={refreshing}
          onRefresh={handleRefresh}
          contentContainerStyle={notifications.length === 0 ? styles.empty : undefined}
          ListEmptyComponent={<EmptyState title={t('notifications.noNotifications')} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  markAllRow: {
    alignItems: 'flex-end',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[1],
  },
  empty: {
    flex: 1,
  },
});
