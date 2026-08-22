import React, { useRef, useCallback } from 'react';
import { View, ScrollView, TextInput, StyleSheet, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { spacing } from '@itour/shared';
import { Button, Input } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { useBookingStore } from '../stores/booking-store';
import { StepIndicator } from '../components/StepIndicator';
import { PriceSummary } from '../components/PriceSummary';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';

export function GuestDetailsScreen() {
  const navigation = useNavigation<Nav>();
  const store = useBookingStore();

  const emailRef = useRef<TextInput>(null);
  const phoneRef = useRef<TextInput>(null);
  const countryRef = useRef<TextInput>(null);
  const flightRef = useRef<TextInput>(null);
  const carrierRef = useRef<TextInput>(null);
  const terminalRef = useRef<TextInput>(null);
  const notesRef = useRef<TextInput>(null);

  const handleNext = useCallback(() => {
    if (!store.guestName.trim()) {
      Alert.alert('Required', 'Please enter your name.');
      return;
    }
    if (!store.guestEmail.trim()) {
      Alert.alert('Required', 'Please enter your email address.');
      return;
    }
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(store.guestEmail.trim())) {
      Alert.alert('Invalid Email', 'Please enter a valid email address.');
      return;
    }
    if (!store.guestPhone.trim()) {
      Alert.alert('Required', 'Please enter your phone number.');
      return;
    }
    navigation.navigate('Payment');
  }, [navigation, store.guestName, store.guestEmail, store.guestPhone]);

  return (
    <View style={styles.container}>
      <StepIndicator currentStep={3} />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <Input
          label="Full Name *"
          placeholder="John Doe"
          value={store.guestName}
          onChangeText={(v) => store.setField('guestName', v)}
          returnKeyType="next"
          onSubmitEditing={() => emailRef.current?.focus()}
          autoCapitalize="words"
        />

        <Input
          ref={emailRef}
          label="Email *"
          placeholder="john@example.com"
          value={store.guestEmail}
          onChangeText={(v) => store.setField('guestEmail', v)}
          keyboardType="email-address"
          autoCapitalize="none"
          returnKeyType="next"
          onSubmitEditing={() => phoneRef.current?.focus()}
        />

        <Input
          ref={phoneRef}
          label="Phone *"
          placeholder="+20 100 123 4567"
          value={store.guestPhone}
          onChangeText={(v) => store.setField('guestPhone', v)}
          keyboardType="phone-pad"
          returnKeyType="next"
          onSubmitEditing={() => countryRef.current?.focus()}
        />

        <Input
          ref={countryRef}
          label="Country"
          placeholder="e.g. United Kingdom"
          value={store.guestCountry}
          onChangeText={(v) => store.setField('guestCountry', v)}
          returnKeyType="next"
          onSubmitEditing={() => flightRef.current?.focus()}
        />

        <Input
          ref={flightRef}
          label="Flight Number"
          placeholder="e.g. MS 777"
          value={store.flightNo}
          onChangeText={(v) => store.setField('flightNo', v)}
          autoCapitalize="characters"
          returnKeyType="next"
          onSubmitEditing={() => carrierRef.current?.focus()}
        />

        <Input
          ref={carrierRef}
          label="Carrier / Airline"
          placeholder="e.g. EgyptAir"
          value={store.carrier}
          onChangeText={(v) => store.setField('carrier', v)}
          returnKeyType="next"
          onSubmitEditing={() => terminalRef.current?.focus()}
        />

        <Input
          ref={terminalRef}
          label="Terminal"
          placeholder="e.g. Terminal 2"
          value={store.terminal}
          onChangeText={(v) => store.setField('terminal', v)}
          returnKeyType="next"
          onSubmitEditing={() => notesRef.current?.focus()}
        />

        <Input
          ref={notesRef}
          label="Notes"
          placeholder="Any special requests..."
          value={store.notes}
          onChangeText={(v) => store.setField('notes', v)}
          multiline
          numberOfLines={3}
          style={{ height: 80, textAlignVertical: 'top' }}
          returnKeyType="done"
        />

        {/* Price summary */}
        <PriceSummary
          price={store.quotePrice}
          currency={store.quoteCurrency}
          paxCount={store.paxCount}
          extras={store.extras}
        />

        {/* Next Button */}
        <View style={styles.buttonContainer}>
          <Button
            title="Continue to Payment"
            onPress={handleNext}
            variant="primary"
            size="lg"
            style={{ backgroundColor: BLUE_PRIMARY }}
          />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing[5],
    paddingBottom: spacing[10],
  },
  buttonContainer: {
    marginTop: spacing[8],
  },
});
