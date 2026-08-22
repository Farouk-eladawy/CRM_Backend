import React, { useEffect, useState, useCallback } from 'react';
import { View, ScrollView, Text, StyleSheet, Alert } from 'react-native';
import type { StackScreenProps } from '@react-navigation/stack';
import {
  driverPortalApi,
  getColors,
  spacing,
  typography,
  formatTime,
  formatDate,
  formatCurrency,
  getOriginLabel,
  getDestinationLabel,
  useT,
  callPhone,
  openWhatsApp,
  getCurrentPosition,
  type DriverPortalJob,
  type Currency,
} from '@itour/shared';
import { Card, StatusBadge, ServiceTypeBadge, Button, LoadingSpinner } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { CollectionCard } from '../components/CollectionCard';

type Props = StackScreenProps<RootStackParamList, 'JobDetail'>;

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  const colors = getColors();
  if (!value) return null;
  return (
    <View style={styles.row}>
      <Text style={[typography.caption, { color: colors.mutedForeground, width: 120 }]}>{label}</Text>
      <Text style={[typography.bodySm, { color: colors.foreground, flex: 1 }]}>{value}</Text>
    </View>
  );
}

export function JobDetailScreen({ route, navigation }: Props) {
  const { jobId } = route.params;
  const colors = getColors();
  const t = useT();
  const [job, setJob] = useState<DriverPortalJob | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchJob = useCallback(async () => {
    try {
      const { data } = await driverPortalApi.getJobs(new Date().toISOString().split('T')[0]);
      const list = Array.isArray(data) ? data : (data as any)?.data ?? [];
      const found = list.find((j: DriverPortalJob) => j.id === jobId);
      setJob(found || null);
    } catch {
      Alert.alert(t('common.error'), t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [jobId, t]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  const handleStatusUpdate = async (status: string) => {
    if (!job) return;
    if (status === 'COMPLETED' && job.collectionRequired && !job.collectionCollected) {
      Alert.alert(t('common.error'), t('driver.mustCollectFirst'));
      return;
    }
    const msg = status === 'IN_PROGRESS' ? t('driver.confirmStart') : t('driver.confirmComplete');
    Alert.alert(t('common.confirm'), msg, [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.confirm'),
        onPress: async () => {
          try {
            // Capture GPS location with status update
            let lat: number | undefined;
            let lng: number | undefined;
            try {
              const pos = await getCurrentPosition();
              lat = pos.lat;
              lng = pos.lng;
            } catch {
              // Continue without GPS if unavailable
            }
            await driverPortalApi.updateJobStatus(job.id, status, lat, lng);
            fetchJob();
          } catch (err: any) {
            Alert.alert(t('common.error'), err?.response?.data?.message || t('common.error'));
          }
        },
      },
    ]);
  };

  const handleMarkCollection = async () => {
    if (!job) return;
    try {
      await driverPortalApi.markCollection(job.id);
      fetchJob();
    } catch (err: any) {
      Alert.alert(t('common.error'), err?.response?.data?.message || t('common.error'));
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;
  if (!job) return null;

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
      <Card style={styles.card}>
        <View style={styles.headerRow}>
          <ServiceTypeBadge serviceType={job.serviceType} />
          <StatusBadge status={job.driverStatus || job.status} />
        </View>
        <Text style={[typography.h3, { color: colors.foreground, marginTop: spacing[2] }]}>
          {job.internalRef}
        </Text>
      </Card>

      <Card style={styles.card}>
        <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
          {t('jobs.route')}
        </Text>
        <InfoRow label={t('booking.from')} value={getOriginLabel(job)} />
        <InfoRow label={t('booking.to')} value={getDestinationLabel(job)} />
        <InfoRow label={t('jobs.pax')} value={`${job.paxCount}`} />
        <InfoRow label={t('booking.date')} value={formatDate(job.jobDate)} />
        <InfoRow label={t('jobs.pickupTime')} value={formatTime(job.pickUpTime)} />
      </Card>

      {job.flight && (
        <Card style={styles.card}>
          <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
            {t('jobs.flight')}
          </Text>
          <InfoRow label="Flight No" value={job.flight.flightNo} />
          <InfoRow label="Carrier" value={job.flight.carrier} />
          <InfoRow label="Terminal" value={job.flight.terminal} />
          <InfoRow label={t('jobs.arrivalTime')} value={formatTime(job.flight.arrivalTime)} />
          <InfoRow label={t('jobs.departureTime')} value={formatTime(job.flight.departureTime)} />
        </Card>
      )}

      {job.clientName && (
        <Card style={styles.card}>
          <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
            Client
          </Text>
          <InfoRow label={t('jobs.clientName')} value={job.clientName} />
          <InfoRow label={t('jobs.clientMobile')} value={job.clientMobile} />
          {job.clientMobile && (
            <View style={styles.contactButtons}>
              <Button
                title="Call"
                variant="outline"
                size="sm"
                onPress={() => callPhone(job.clientMobile!, job.clientName)}
                style={{ flex: 1 }}
              />
              <Button
                title="WhatsApp"
                variant="outline"
                size="sm"
                onPress={() => openWhatsApp(job.clientMobile!)}
                style={{ flex: 1 }}
              />
            </View>
          )}
        </Card>
      )}

      {job.assignment?.vehicle && (
        <Card style={styles.card}>
          <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[2] }]}>
            {t('jobs.vehicle')}
          </Text>
          <InfoRow label="Plate" value={job.assignment.vehicle.plateNumber} />
          <InfoRow label="Type" value={job.assignment.vehicle.vehicleType?.name} />
        </Card>
      )}

      {job.collectionRequired && (
        <Card style={styles.card}>
          <CollectionCard
            amount={job.collectionAmount}
            currency={job.collectionCurrency}
            collected={job.collectionCollected}
            onMarkCollected={handleMarkCollection}
          />
        </Card>
      )}

      {job.notes && (
        <Card style={styles.card}>
          <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[1] }]}>
            {t('jobs.notes')}
          </Text>
          <Text style={[typography.bodySm, { color: colors.mutedForeground }]}>{job.notes}</Text>
        </Card>
      )}

      <View style={styles.actions}>
        {job.driverStatus === 'PENDING' && (
          <>
            <Button
              title={t('driver.startTrip')}
              onPress={() => handleStatusUpdate('IN_PROGRESS')}
              size="lg"
            />
            <Button
              title={t('driver.noShow')}
              variant="destructive"
              onPress={() => navigation.navigate('NoShow', { jobId: job.id })}
              size="lg"
              style={{ marginTop: spacing[2] }}
            />
          </>
        )}
        {job.driverStatus === 'IN_PROGRESS' && (
          <>
            <Button
              title={t('driver.completeTrip')}
              onPress={() => handleStatusUpdate('COMPLETED')}
              size="lg"
            />
            <Button
              title={t('driver.noShow')}
              variant="destructive"
              onPress={() => navigation.navigate('NoShow', { jobId: job.id })}
              size="lg"
              style={{ marginTop: spacing[2] }}
            />
          </>
        )}
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
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: spacing[1],
  },
  contactButtons: {
    flexDirection: 'row',
    gap: spacing[2],
    marginTop: spacing[2],
  },
  actions: {
    padding: spacing[4],
    paddingBottom: spacing[10],
  },
});
