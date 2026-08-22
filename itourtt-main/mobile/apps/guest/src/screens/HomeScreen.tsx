import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { spacing, borderRadius, typography, useTheme, getColors, type ThemeMode } from '@itour/shared';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { useBookingStore } from '../stores/booking-store';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';
const BLUE_DARK = '#1E3A5F';
const BLUE_LIGHT = '#DBEAFE';

const THEME_OPTIONS: { value: ThemeMode; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];

export function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const insets = useSafeAreaInsets();
  const reset = useBookingStore((s) => s.reset);
  const { mode, setMode, isDark } = useTheme();
  const colors = getColors();
  const [showThemePicker, setShowThemePicker] = useState(false);

  const handleBookTransfer = () => {
    reset();
    navigation.navigate('Search');
  };

  const handleTrackBooking = () => {
    navigation.navigate('BookingLookup');
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top, backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} backgroundColor={colors.background} />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={[typography.h1, { color: colors.foreground }]}>iTour</Text>
            <Text style={[typography.body, { color: colors.mutedForeground, marginTop: spacing[1] }]}>
              Airport transfers made simple
            </Text>
          </View>
          <TouchableOpacity
            style={[styles.gearButton, { backgroundColor: colors.muted }]}
            onPress={() => setShowThemePicker(!showThemePicker)}
          >
            <Text style={{ fontSize: 20, color: colors.foreground }}>{'*'}</Text>
          </TouchableOpacity>
        </View>
        {showThemePicker && (
          <View style={[styles.themeRow, { marginTop: spacing[3] }]}>
            {THEME_OPTIONS.map((opt) => {
              const isActive = mode === opt.value;
              return (
                <TouchableOpacity
                  key={opt.value}
                  style={[
                    styles.themeButton,
                    {
                      backgroundColor: isActive ? BLUE_PRIMARY : colors.muted,
                      borderColor: isActive ? BLUE_PRIMARY : colors.border,
                    },
                  ]}
                  onPress={() => setMode(opt.value)}
                >
                  <Text
                    style={[
                      typography.bodySm,
                      {
                        color: isActive ? '#FFFFFF' : colors.foreground,
                        textAlign: 'center',
                      },
                    ]}
                  >
                    {opt.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}
      </View>

      {/* Cards */}
      <View style={styles.cardsContainer}>
        {/* Book a Transfer Card */}
        <TouchableOpacity
          style={[styles.card, styles.bookCard]}
          onPress={handleBookTransfer}
          activeOpacity={0.85}
        >
          <View style={styles.cardIconCircle}>
            <Text style={styles.cardIcon}>{'>'}</Text>
          </View>
          <Text style={[typography.h2, { color: '#FFFFFF', marginTop: spacing[4] }]}>
            Book a Transfer
          </Text>
          <Text style={[typography.body, { color: '#BFDBFE', marginTop: spacing[1] }]}>
            Airport pickups, drop-offs, and city transfers across Egypt
          </Text>
          <View style={styles.cardAction}>
            <Text style={[typography.buttonSm, { color: '#FFFFFF' }]}>Get Started</Text>
            <Text style={[typography.buttonSm, { color: '#FFFFFF', marginLeft: spacing[1] }]}>
              {' ->'}
            </Text>
          </View>
        </TouchableOpacity>

        {/* Track My Booking Card */}
        <TouchableOpacity
          style={[styles.card, styles.trackCard]}
          onPress={handleTrackBooking}
          activeOpacity={0.85}
        >
          <View style={[styles.cardIconCircle, { backgroundColor: BLUE_PRIMARY + '20' }]}>
            <Text style={[styles.cardIcon, { color: BLUE_PRIMARY }]}>{'?'}</Text>
          </View>
          <Text style={[typography.h2, { color: '#09090B', marginTop: spacing[4] }]}>
            Track My Booking
          </Text>
          <Text style={[typography.body, { color: '#71717A', marginTop: spacing[1] }]}>
            Look up your booking status using your reference number
          </Text>
          <View style={styles.cardAction}>
            <Text style={[typography.buttonSm, { color: BLUE_PRIMARY }]}>Look Up</Text>
            <Text style={[typography.buttonSm, { color: BLUE_PRIMARY, marginLeft: spacing[1] }]}>
              {' ->'}
            </Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* Footer */}
      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing[4] }]}>
        <Text style={[typography.caption, { color: colors.mutedForeground, textAlign: 'center' }]}>
          iTour Transport & Traffic
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingHorizontal: spacing[6],
    paddingTop: spacing[8],
    paddingBottom: spacing[4],
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  gearButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing[1],
  },
  themeRow: {
    flexDirection: 'row',
    gap: spacing[2],
  },
  themeButton: {
    flex: 1,
    paddingVertical: spacing[2],
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  cardsContainer: {
    flex: 1,
    paddingHorizontal: spacing[5],
    paddingTop: spacing[2],
    gap: spacing[4],
  },
  card: {
    flex: 1,
    borderRadius: borderRadius['2xl'],
    padding: spacing[6],
    justifyContent: 'flex-start',
  },
  bookCard: {
    backgroundColor: BLUE_PRIMARY,
  },
  trackCard: {
    backgroundColor: BLUE_LIGHT,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  cardIconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardIcon: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  cardAction: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing[4],
  },
  footer: {
    paddingHorizontal: spacing[6],
    paddingTop: spacing[2],
  },
});
