import React from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { spacing, useT, type RepPortalJob } from '@itour/shared';
import { Button } from '@itour/ui';

interface RepJobActionsProps {
  job: RepPortalJob;
  onCompleteTrip: () => void;
  onNoShow: () => void;
}

export function RepJobActions({ job, onCompleteTrip, onNoShow }: RepJobActionsProps) {
  const t = useT();
  const status = job.repStatus;

  const handleComplete = () => {
    Alert.alert(t('common.confirm'), t('rep.confirmComplete'), [
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
            title="Complete Job"
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
