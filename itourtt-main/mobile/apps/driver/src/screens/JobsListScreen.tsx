import React, { useState, useCallback, useEffect } from 'react';
import { View, FlatList, StyleSheet, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  driverPortalApi,
  today,
  getColors,
  spacing,
  useRefresh,
  useT,
  getCurrentPosition,
  type DriverPortalJob,
} from '@itour/shared';
import { DateNavigator, JobCard, EmptyState, LoadingSpinner, ErrorBanner, SkeletonList } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { DriverJobActions } from '../components/DriverJobActions';
import { CollectionCard } from '../components/CollectionCard';

type Nav = StackNavigationProp<RootStackParamList>;

export function JobsListScreen() {
  const navigation = useNavigation<Nav>();
  const colors = getColors();
  const t = useT();
  const [date, setDate] = useState(today());
  const [jobs, setJobs] = useState<DriverPortalJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setError(null);
    try {
      const { data } = await driverPortalApi.getJobs(date);
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
        let lat: number | undefined;
        let lng: number | undefined;
        try {
          const pos = await getCurrentPosition();
          lat = pos.lat;
          lng = pos.lng;
        } catch {
          // Continue without GPS
        }
        await driverPortalApi.updateJobStatus(jobId, status, lat, lng);
        await fetchJobs();
      } catch (err: any) {
        Alert.alert(t('common.error'), err?.response?.data?.message || t('common.error'));
      }
    },
    [fetchJobs, t],
  );

  const handleMarkCollection = useCallback(
    async (jobId: string) => {
      try {
        await driverPortalApi.markCollection(jobId);
        await fetchJobs();
      } catch (err: any) {
        Alert.alert(t('common.error'), err?.response?.data?.message || t('common.error'));
      }
    },
    [fetchJobs, t],
  );

  const renderItem = useCallback(
    ({ item }: { item: DriverPortalJob }) => (
      <JobCard
        job={item}
        portalStatus={item.driverStatus}
        onPress={() => navigation.navigate('JobDetail', { jobId: item.id })}
        bottomContent={
          <View>
            {item.collectionRequired && (
              <CollectionCard
                amount={item.collectionAmount}
                currency={item.collectionCurrency}
                collected={item.collectionCollected}
                onMarkCollected={() => handleMarkCollection(item.id)}
              />
            )}
            <DriverJobActions
              job={item}
              onStartTrip={() => handleStatusUpdate(item.id, 'IN_PROGRESS')}
              onCompleteTrip={() => handleStatusUpdate(item.id, 'COMPLETED')}
              onNoShow={() => navigation.navigate('NoShow', { jobId: item.id })}
            />
          </View>
        }
      />
    ),
    [navigation, handleStatusUpdate, handleMarkCollection],
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
