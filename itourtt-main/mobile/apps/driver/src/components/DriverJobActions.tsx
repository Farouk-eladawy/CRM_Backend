import React from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { spacing, useT, type DriverPortalJob } from '@itour/shared';
import { Button } from '@itour/ui';

interface DriverJobActionsProps {
  job: DriverPortalJob;
  onStartTrip: () => void;
  onCompleteTrip: () => void;
  onNoShow: () => void;
}

export function DriverJobActions({ job, onStartTrip, onCompleteTrip, onNoShow }: DriverJobActionsProps) {
  const t = useT();
  const status = job.driverStatus;

  const handleComplete = () => {
    if (job.collectionRequired && !job.collectionCollected) {
      Alert.alert(t('common.error'), t('driver.mustCollectFirst'));
      return;
    }
    Alert.alert(t('common.confirm'), t('driver.confirmComplete'), [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('common.confirm'), onPress: onCompleteTrip },
    ]);
  };

  if (status === 'COMPLETED' || status === 'CANCELLED' || status === 'NO_SHOW') {
    return null;
  }

  return (
    <View style={styles.container}>
      {status === 'PENDING' && (
        <View style={styles.row}>
          <Button
            title={t('driver.startTrip')}
            onPress={() => {
              Alert.alert(t('common.confirm'), t('driver.confirmStart'), [
                { text: t('common.cancel'), style: 'cancel' },
                { text: t('common.confirm'), onPress: onStartTrip },
              ]);
            }}
            size="sm"
            style={styles.flex}
          />
          <Button
            title={t('driver.noShow')}
            variant="destructive"
            onPress={onNoShow}
            size="sm"
            style={styles.flex}
          />
        </View>
      )}
      {status === 'IN_PROGRESS' && (
        <View style={styles.row}>
          <Button
            title={t('driver.completeTrip')}
            onPress={handleComplete}
            size="sm"
            style={styles.flex}
          />
          <Button
            title={t('driver.noShow')}
            variant="destructive"
            onPress={onNoShow}
            size="sm"
            style={styles.flex}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: spacing[2],
  },
  row: {
    flexDirection: 'row',
    gap: spacing[2],
  },
  flex: {
    flex: 1,
  },
});
