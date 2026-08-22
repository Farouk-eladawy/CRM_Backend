import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { getColors, useT } from '@itour/shared';
import { DashboardScreen } from '../screens/DashboardScreen';
import { JobsListScreen } from '../screens/JobsListScreen';
import { ProfileScreen } from '../screens/ProfileScreen';

export type MainTabParamList = {
  Dashboard: undefined;
  Jobs: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabParamList>();

export function MainTabNavigator() {
  const colors = getColors();
  const t = useT();

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
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: t('tabs.dashboard'),
          tabBarLabel: t('tabs.dashboard'),
        }}
      />
      <Tab.Screen
        name="Jobs"
        component={JobsListScreen}
        options={{
          title: t('jobs.todayJobs'),
          tabBarLabel: t('tabs.jobs'),
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
