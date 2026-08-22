import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { publicApi, spacing, typography } from '@itour/shared';
import { Button, Input, LoadingSpinner } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';

export function BookingLookupScreen() {
  const navigation = useNavigation<Nav>();
  const [refInput, setRefInput] = useState('');
  const [emailInput, setEmailInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLookup = useCallback(async () => {
    const trimmed = refInput.trim();
    const email = emailInput.trim();
    if (!trimmed) {
      Alert.alert('Enter Reference', 'Please enter your booking reference number.');
      return;
    }
    if (!email) {
      Alert.alert('Enter Email', 'Please enter the email address used for the booking.');
      return;
    }

    setLoading(true);
    try {
      const { data: resData } = await publicApi.getBooking(trimmed, email);
      const booking = (resData as any)?.data ?? resData;
      if (!booking || (!booking.bookingRef && !booking.id)) {
        Alert.alert('Not Found', 'No booking found with that reference and email.');
        return;
      }
      navigation.navigate('BookingDetail', { bookingRef: trimmed, email });
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 404) {
        Alert.alert('Not Found', 'No booking found for that reference and email.');
      } else {
        Alert.alert('Error', err?.response?.data?.message || err?.message || 'Something went wrong.');
      }
    } finally {
      setLoading(false);
    }
  }, [refInput, emailInput, navigation]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.content}>
        <View style={styles.iconCircle}>
          <Text style={styles.iconText}>{'?'}</Text>
        </View>

        <Text style={[typography.h3, { color: '#09090B', textAlign: 'center' }]}>
          Track Your Booking
        </Text>
        <Text
          style={[
            typography.body,
            { color: '#71717A', textAlign: 'center', marginTop: spacing[2], marginBottom: spacing[6] },
          ]}
        >
          Enter the reference number you received when you made your booking.
        </Text>

        <Input
          label="Booking Reference"
          placeholder="e.g. ITOUR-ABC123"
          value={refInput}
          onChangeText={setRefInput}
          autoCapitalize="characters"
          returnKeyType="next"
          containerStyle={{ width: '100%' }}
        />

        <Input
          label="Email"
          placeholder="Email used for the booking"
          value={emailInput}
          onChangeText={setEmailInput}
          autoCapitalize="none"
          keyboardType="email-address"
          returnKeyType="search"
          onSubmitEditing={handleLookup}
          containerStyle={{ width: '100%' }}
        />

        {loading ? (
          <LoadingSpinner message="Looking up your booking..." />
        ) : (
          <Button
            title="Look Up"
            onPress={handleLookup}
            variant="primary"
            size="lg"
            style={{ backgroundColor: BLUE_PRIMARY, marginTop: spacing[2], width: '100%' }}
          />
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    flex: 1,
    padding: spacing[5],
    paddingTop: spacing[10],
    alignItems: 'center',
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing[5],
  },
  iconText: {
    fontSize: 28,
    fontWeight: '700',
    color: BLUE_PRIMARY,
  },
});
