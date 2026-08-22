import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { getColors, spacing, typography, formatDate, addDays, today, useT } from '@itour/shared';

interface DateNavigatorProps {
  date: string;
  onDateChange: (date: string) => void;
}

export function DateNavigator({ date, onDateChange }: DateNavigatorProps) {
  const colors = getColors();
  const t = useT();
  const isToday = date === today();

  return (
    <View style={[styles.container, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <TouchableOpacity
        onPress={() => onDateChange(addDays(date, -1))}
        style={styles.arrow}
        hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
      >
        <Text style={[typography.h3, { color: colors.foreground }]}>{'\u2039'}</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => onDateChange(today())} style={styles.center}>
        <Text style={[typography.bodyMedium, { color: colors.foreground }]}>{formatDate(date)}</Text>
        {!isToday && (
          <Text style={[typography.caption, { color: colors.primary, marginTop: 2 }]}>
            {t('common.today')}
          </Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        onPress={() => onDateChange(addDays(date, 1))}
        style={styles.arrow}
        hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
      >
        <Text style={[typography.h3, { color: colors.foreground }]}>{'\u203A'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
    borderRadius: 12,
    borderWidth: 1,
  },
  arrow: {
    width: 40,
    alignItems: 'center',
  },
  center: {
    alignItems: 'center',
  },
});
