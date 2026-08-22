import React, { useEffect, useState, useCallback } from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { getColors, repPortalApi, useT } from '@itour/shared';
import { JobsListScreen } from '../screens/JobsListScreen';
import { HistoryScreen } from '../screens/HistoryScreen';
import { NotificationsScreen } from '../screens/NotificationsScreen';
import { ProfileScreen } from '../screens/ProfileScreen';

export type MainTabParamList = {
  Jobs: undefined;
  History: undefined;
  Notifications: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabParamList>();

export function MainTabNavigator() {
  const colors = getColors();
  const t = useT();
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const { data } = await repPortalApi.getNotifications();
      const notifications = Array.isArray(data) ? data : (data as any)?.data ?? [];
      setUnreadCount(notifications.filter((n: any) => !n.isRead).length);
    } catch {
      // Ignore errors for badge count
    }
  }, []);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.mutedForeground,
        tabBarStyle: {
          backgroundColor: colors.card,
          borderTopColor: colors.border,
        },
        headerStyle: {
          backgroundColor: colors.card,
        },
        headerTintColor: colors.foreground,
      }}
    >
      <Tab.Screen
        name="Jobs"
        component={JobsListScreen}
        options={{
          title: t('jobs.todayJobs'),
          tabBarLabel: t('tabs.jobs'),
        }}
      />
      <Tab.Screen
        name="History"
        component={HistoryScreen}
        options={{
          title: t('jobs.history'),
          tabBarLabel: t('tabs.history'),
        }}
      />
      <Tab.Screen
        name="Notifications"
        component={NotificationsScreen}
        options={{
          title: t('notifications.title'),
          tabBarLabel: t('tabs.notifications'),
          tabBarBadge: unreadCount > 0 ? unreadCount : undefined,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: t('profile.title'),
          tabBarLabel: t('tabs.profile'),
        }}
      />
    </Tab.Navigator>
  );
}
