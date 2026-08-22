import React, { useState, useCallback } from 'react';
import { View, FlatList, Text, StyleSheet } from 'react-native';
import {
  driverPortalApi,
  getColors,
  spacing,
  typography,
  formatCurrency,
  useRefresh,
  useT,
  type DriverPortalJob,
} from '@itour/shared';
import { JobCard, EmptyState, LoadingSpinner, Button, SkeletonList } from '@itour/ui';

export function HistoryScreen() {
  const colors = getColors();
  const t = useT();
  const [jobs, setJobs] = useState<DriverPortalJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState(() => {
    const now = new Date();
    const from = new Date(now);
    from.setDate(from.getDate() - 30);
    return {
      from: from.toISOString().split('T')[0],
      to: now.toISOString().split('T')[0],
    };
  });

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await driverPortalApi.getJobHistory(dateRange.from, dateRange.to);
      const list = Array.isArray(data) ? data : (data as any)?.data ?? [];
      setJobs(list);
    } catch {
      // handled silently
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  React.useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const { refreshing, handleRefresh } = useRefresh(fetchHistory);

  const totalEarnings = jobs.reduce((sum, j) => sum + (j.feeEarned || 0), 0);

  const renderItem = useCallback(
    ({ item }: { item: DriverPortalJob }) => (
      <JobCard
        job={item}
        portalStatus={item.driverStatus}
        rightContent={
          item.feeEarned ? (
            <Text style={[typography.bodySmMedium, { color: colors.foreground }]}>
              {formatCurrency(item.feeEarned, 'EGP')}
            </Text>
          ) : undefined
        }
      />
    ),
    [colors],
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={[styles.summary, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <Text style={[typography.caption, { color: colors.mutedForeground }]}>
          {dateRange.from} - {dateRange.to}
        </Text>
        <Text style={[typography.h3, { color: colors.foreground, marginTop: spacing[1] }]}>
          {formatCurrency(totalEarnings, 'EGP')}
        </Text>
        <Text style={[typography.caption, { color: colors.mutedForeground }]}>
          {jobs.length} trips
        </Text>
      </View>

      {loading && !refreshing ? (
        <SkeletonList />
      ) : (
        <FlatList
          data={jobs}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          refreshing={refreshing}
          onRefresh={handleRefresh}
          contentContainerStyle={jobs.length === 0 ? styles.empty : styles.list}
          ListEmptyComponent={<EmptyState title={t('jobs.noJobs')} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  summary: {
    alignItems: 'center',
    padding: spacing[4],
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
    borderRadius: 12,
    borderWidth: 1,
  },
  list: {
    paddingBottom: spacing[4],
  },
  empty: {
    flex: 1,
  },
});
