import React, { useState, useCallback, useEffect } from 'react';
import { View, FlatList, StyleSheet, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  repPortalApi,
  today,
  getColors,
  spacing,
  useRefresh,
  useT,
  type RepPortalJob,
} from '@itour/shared';
import { DateNavigator, JobCard, EmptyState, LoadingSpinner, ErrorBanner, SkeletonList } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { RepJobActions } from '../components/RepJobActions';

type Nav = StackNavigationProp<RootStackParamList>;

export function JobsListScreen() {
  const navigation = useNavigation<Nav>();
  const colors = getColors();
  const t = useT();
  const [date, setDate] = useState(today());
  const [jobs, setJobs] = useState<RepPortalJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setError(null);
    try {
      const { data } = await repPortalApi.getJobs(date);
      const list = Array.isArray(data) ? data : (data as any)?.data ?? [];
      setJobs(list);
    } catch (err: any) {
      setError(err?.message || t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [date, t]);

  useEffect(() => {
    setLoading(true);
    fetchJobs();
  }, [fetchJobs]);

  const { refreshing, handleRefresh } = useRefresh(fetchJobs);

  const handleStatusUpdate = useCallback(
    async (jobId: string, status: string) => {
      try {
        await repPortalApi.updateJobStatus(jobId, status);
        await fetchJobs();
      } catch (err: any) {
        Alert.alert(t('common.error'), err?.response?.data?.message || t('common.error'));
      }
    },
    [fetchJobs, t],
  );

  const renderItem = useCallback(
    ({ item }: { item: RepPortalJob }) => (
      <JobCard
        job={item}
        portalStatus={item.repStatus}
        onPress={() => navigation.navigate('JobDetail', { jobId: item.id })}
        bottomContent={
          <RepJobActions
            job={item}
            onCompleteTrip={() => handleStatusUpdate(item.id, 'COMPLETED')}
            onNoShow={() => navigation.navigate('NoShow', { jobId: item.id })}
          />
        }
      />
    ),
    [navigation, handleStatusUpdate],
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <DateNavigator date={date} onDateChange={setDate} />

      {error && <ErrorBanner message={error} onRetry={fetchJobs} />}

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
