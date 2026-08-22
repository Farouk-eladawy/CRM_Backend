import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import {
  supplierPortalApi,
  today,
  getColors,
  spacing,
  typography,
  useRefresh,
  useT,
  type SupplierPortalJob,
  type SupplierProfile,
} from '@itour/shared';
import { Card, LoadingSpinner, ErrorBanner } from '@itour/ui';
import { FleetOverview } from '../components/FleetOverview';

export function DashboardScreen() {
  const colors = getColors();
  const t = useT();
  const [jobs, setJobs] = useState<SupplierPortalJob[]>([]);
  const [profile, setProfile] = useState<SupplierProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setError(null);
    try {
      const [jobsRes, profileRes] = await Promise.all([
        supplierPortalApi.getJobs(today()),
        supplierPortalApi.getProfile(),
      ]);
      const jobList = Array.isArray(jobsRes.data) ? jobsRes.data : (jobsRes.data as any)?.data ?? [];
      setJobs(jobList);
      setProfile((profileRes.data as any)?.data ?? profileRes.data);
    } catch (err: any) {
      setError(err?.message || t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const { refreshing, handleRefresh } = useRefresh(fetchData);

  const pendingCount = jobs.filter((j) => j.supplierStatus === 'PENDING').length;
  const inProgressCount = jobs.filter((j) => j.supplierStatus === 'IN_PROGRESS').length;
  const completedCount = jobs.filter((j) => j.supplierStatus === 'COMPLETED').length;

  if (loading && !refreshing) return <LoadingSpinner fullScreen />;

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      {error && <ErrorBanner message={error} onRetry={fetchData} />}

      {profile && (
        <Card style={styles.card}>
          <Text style={[typography.h3, { color: colors.foreground }]}>
            {profile.tradeName || profile.legalName}
          </Text>
          <Text style={[typography.caption, { color: colors.mutedForeground, marginTop: spacing[1] }]}>
            {t('tabs.dashboard')}
          </Text>
        </Card>
      )}

      <Card style={styles.card}>
        <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[3] }]}>
          Today's Jobs
        </Text>
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={[typography.h2, { color: colors.foreground }]}>{jobs.length}</Text>
            <Text style={[typography.caption, { color: colors.mutedForeground }]}>Total</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[typography.h2, { color: colors.primary }]}>{pendingCount}</Text>
            <Text style={[typography.caption, { color: colors.mutedForeground }]}>Pending</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[typography.h2, { color: colors.foreground }]}>{inProgressCount}</Text>
            <Text style={[typography.caption, { color: colors.mutedForeground }]}>In Progress</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[typography.h2, { color: colors.foreground }]}>{completedCount}</Text>
            <Text style={[typography.caption, { color: colors.mutedForeground }]}>Completed</Text>
          </View>
        </View>
      </Card>

      {profile && <FleetOverview profile={profile} />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingBottom: spacing[10],
  },
  card: {
    marginHorizontal: spacing[4],
    marginTop: spacing[3],
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
});
