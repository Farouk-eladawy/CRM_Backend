import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import {
  getColors,
  spacing,
  typography,
  formatCurrency,
  useT,
  type Currency,
} from '@itour/shared';
import { Button, Badge } from '@itour/ui';

interface CollectionCardProps {
  amount: number | null;
  currency: Currency | null;
  collected: boolean;
  onMarkCollected: () => void;
}

export function CollectionCard({ amount, currency, collected, onMarkCollected }: CollectionCardProps) {
  const colors = getColors();
  const t = useT();

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <View>
          <Text style={[typography.caption, { color: colors.mutedForeground }]}>
            {t('driver.collectionAmount')}
          </Text>
          <Text style={[typography.h4, { color: colors.foreground }]}>
            {amount ? formatCurrency(amount, currency || 'EGP') : '\u2014'}
          </Text>
        </View>
        <Badge
          label={collected ? t('driver.collectionCollected') : t('driver.collectionPending')}
          backgroundColor={collected ? '#ECFDF5' : '#FEF2F2'}
          textColor={collected ? '#059669' : '#DC2626'}
        />
      </View>

      {!collected && (
        <Button
          title={t('driver.markCollection')}
          variant="outline"
          size="sm"
          onPress={onMarkCollected}
          style={{ marginTop: spacing[2] }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing[1],
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
});
