import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, Alert, TouchableOpacity } from 'react-native';
import {
  driverPortalApi,
  useAuthStore,
  getColors,
  spacing,
  typography,
  useT,
  useTheme,
  type DriverProfile,
  type ThemeMode,
} from '@itour/shared';
import { Card, Button, LoadingSpinner, SkeletonProfile } from '@itour/ui';

const THEME_OPTIONS: { value: ThemeMode; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];

export function ProfileScreen() {
  const colors = getColors();
  const t = useT();
  const { mode, setMode } = useTheme();
  const logout = useAuthStore((s) => s.logout);
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await driverPortalApi.getProfile();
        setProfile((data as any)?.data ?? data);
      } catch {
        // handled silently
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleLogout = () => {
    Alert.alert(t('auth.logout'), 'Are you sure you want to logout?', [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('auth.logout'), style: 'destructive', onPress: () => logout() },
    ]);
  };

  if (loading) return <SkeletonProfile />;

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
      {profile && (
        <>
          <Card style={styles.card}>
            <Text style={[typography.h3, { color: colors.foreground }]}>{profile.name}</Text>
            <View style={styles.field}>
              <Text style={[typography.caption, { color: colors.mutedForeground }]}>
                {t('profile.mobile')}
              </Text>
              <Text style={[typography.bodySm, { color: colors.foreground }]}>
                {profile.mobileNumber}
              </Text>
            </View>
            <View style={styles.field}>
              <Text style={[typography.caption, { color: colors.mutedForeground }]}>
                {t('profile.license')}
              </Text>
              <Text style={[typography.bodySm, { color: colors.foreground }]}>
                {profile.licenseNumber}
              </Text>
            </View>
          </Card>

          {profile.vehicles && profile.vehicles.length > 0 && (
            <Card style={styles.card}>
              <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
                {t('profile.vehicles')}
              </Text>
              {profile.vehicles.map((dv) => (
                <View key={dv.id} style={styles.vehicleRow}>
                  <Text style={[typography.bodySm, { color: colors.foreground }]}>
                    {dv.vehicle?.plateNumber} - {dv.vehicle?.vehicleType?.name}
                  </Text>
                  {dv.isPrimary && (
                    <Text style={[typography.caption, { color: colors.primary }]}>Primary</Text>
                  )}
                </View>
              ))}
            </Card>
          )}
        </>
      )}

      {/* Theme Picker */}
      <Card style={styles.card}>
        <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
          Theme
        </Text>
        <View style={styles.themeRow}>
          {THEME_OPTIONS.map((opt) => {
            const isActive = mode === opt.value;
            return (
              <TouchableOpacity
                key={opt.value}
                style={[
                  styles.themeButton,
                  {
                    backgroundColor: isActive ? colors.primary : colors.muted,
                    borderColor: isActive ? colors.primary : colors.border,
                  },
                ]}
                onPress={() => setMode(opt.value)}
              >
                <Text
                  style={[
                    typography.bodySm,
                    {
                      color: isActive ? colors.primaryForeground : colors.foreground,
                      textAlign: 'center',
                    },
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </Card>

      <View style={styles.logoutSection}>
        <Button
          title={t('auth.logout')}
          variant="destructive"
          onPress={handleLogout}
          size="lg"
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  card: {
    marginHorizontal: spacing[4],
    marginTop: spacing[3],
  },
  field: {
    marginTop: spacing[3],
  },
  vehicleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing[2],
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  themeRow: {
    flexDirection: 'row',
    gap: spacing[2],
  },
  themeButton: {
    flex: 1,
    paddingVertical: spacing[2],
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  logoutSection: {
    padding: spacing[4],
    paddingBottom: spacing[10],
  },
});
