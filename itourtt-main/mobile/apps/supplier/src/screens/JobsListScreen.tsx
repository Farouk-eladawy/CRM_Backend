import React, { useState, useCallback, useEffect } from 'react';
import { View, FlatList, TextInput, StyleSheet, Alert } from 'react-native';
import {
  supplierPortalApi,
  today,
  getColors,
  spacing,
  typography,
  useRefresh,
  useT,
  type SupplierPortalJob,
} from '@itour/shared';
import { DateNavigator, JobCard, EmptyState, LoadingSpinner, ErrorBanner, Button, SkeletonList } from '@itour/ui';

export function JobsListScreen() {
  const colors = getColors();
  const t = useT();
  const [date, setDate] = useState(today());
  const [jobs, setJobs] = useState<SupplierPortalJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const fetchJobs = useCallback(async () => {
    setError(null);
    try {
      const { data } = await supplierPortalApi.getJobs(date);
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

  const handleComplete = useCallback(
    async (jobId: string) => {
      Alert.alert(t('common.confirm'), 'Mark this job as completed?', [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('common.confirm'),
          onPress: async () => {
            try {
              setCompletingId(jobId);
              await supplierPortalApi.completeJob(jobId, notes[jobId] || undefined);
              setNotes((prev) => {
                const next = { ...prev };
                delete next[jobId];
                return next;
              });
              await fetchJobs();
            } catch (err: any) {
              Alert.alert(t('common.error'), err?.response?.data?.message || t('common.error'));
            } finally {
              setCompletingId(null);
            }
          },
        },
      ]);
    },
    [fetchJobs, notes, t],
  );

  const renderItem = useCallback(
    ({ item }: { item: SupplierPortalJob }) => {
      const canComplete =
        item.supplierStatus === 'PENDING' || item.supplierStatus === 'IN_PROGRESS';

      return (
        <JobCard
          job={item}
          portalStatus={item.supplierStatus}
          bottomContent={
            canComplete ? (
              <View style={styles.actions}>
                <TextInput
                  style={[
                    styles.notesInput,
                    {
                      color: colors.foreground,
                      borderColor: colors.border,
                      backgroundColor: colors.background,
                    },
                  ]}
                  placeholder="Notes (optional)"
                  placeholderTextColor={colors.mutedForeground}
                  value={notes[item.id] || ''}
                  onChangeText={(text) =>
                    setNotes((prev) => ({ ...prev, [item.id]: text }))
                  }
                  multiline
                  numberOfLines={2}
                />
                <Button
                  title="Complete"
                  onPress={() => handleComplete(item.id)}
                  loading={completingId === item.id}
                  disabled={completingId !== null}
                  size="sm"
                />
              </View>
            ) : undefined
          }
        />
      );
    },
    [colors, notes, completingId, handleComplete],
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
  actions: {
    marginTop: spacing[2],
    gap: spacing[2],
  },
  notesInput: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    ...typography.bodySm,
    minHeight: 40,
    textAlignVertical: 'top',
  },
});
