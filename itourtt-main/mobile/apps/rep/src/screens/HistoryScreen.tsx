import React, { useState, useCallback } from 'react';
import { View, FlatList, Text, StyleSheet } from 'react-native';
import {
  repPortalApi,
  getColors,
  spacing,
  typography,
  formatCurrency,
  useRefresh,
  useT,
  type RepPortalJob,
} from '@itour/shared';
import { JobCard, EmptyState, LoadingSpinner, SkeletonList } from '@itour/ui';
import { EarningsSummary } from '../components/EarningsSummary';

export function HistoryScreen() {
  const colors = getColors();
  const t = useT();
  const [jobs, setJobs] = useState<RepPortalJob[]>([]);
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
      const { data } = await repPortalApi.getJobHistory(dateRange.from, dateRange.to);
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

  const completedJobs = jobs.filter((j) => j.repStatus === 'COMPLETED');
  const totalEarnings = completedJobs.reduce((sum, j) => sum + (j.feeEarned || 0), 0);

  const renderItem = useCallback(
    ({ item }: { item: RepPortalJob }) => (
      <JobCard
        job={item}
        portalStatus={item.repStatus}
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
      <EarningsSummary
        totalEarnings={totalEarnings}
        completedCount={completedJobs.length}
        dateFrom={dateRange.from}
        dateTo={dateRange.to}
      />

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
  list: {
    paddingBottom: spacing[4],
  },
  empty: {
    flex: 1,
  },
});
