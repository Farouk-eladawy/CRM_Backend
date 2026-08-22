import React, { useCallback } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  spacing,
  borderRadius,
  typography,
  type B2CPaymentMethod,
  type B2CPaymentGateway,
} from '@itour/shared';
import { Button } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { useBookingStore } from '../stores/booking-store';
import { StepIndicator } from '../components/StepIndicator';
import { PriceSummary } from '../components/PriceSummary';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';
const BLUE_LIGHT = '#EFF6FF';

const PAYMENT_METHODS: { value: B2CPaymentMethod; label: string; desc: string }[] = [
  { value: 'PAY_ON_ARRIVAL', label: 'Pay on Arrival', desc: 'Pay your driver in cash upon arrival' },
  { value: 'ONLINE', label: 'Pay Online', desc: 'Secure online payment now' },
];

const GATEWAYS: { value: B2CPaymentGateway; label: string; desc: string }[] = [
  { value: 'STRIPE', label: 'Credit / Debit Card', desc: 'Visa, Mastercard via Stripe' },
  { value: 'EGYPT_BANK', label: 'Egypt Bank', desc: 'Local Egyptian bank transfer' },
  { value: 'DUBAI_BANK', label: 'Dubai Bank', desc: 'UAE bank transfer' },
];

export function PaymentScreen() {
  const navigation = useNavigation<Nav>();
  const store = useBookingStore();

  const handleSelectMethod = useCallback(
    (method: B2CPaymentMethod) => {
      store.setField('paymentMethod', method);
      if (method === 'PAY_ON_ARRIVAL') {
        store.setField('paymentGateway', '');
      }
    },
    [store],
  );

  const handleSelectGateway = useCallback(
    (gw: B2CPaymentGateway) => {
      store.setField('paymentGateway', gw);
    },
    [store],
  );

  const handleConfirm = useCallback(() => {
    if (!store.paymentMethod) {
      Alert.alert('Select Payment', 'Please choose a payment method.');
      return;
    }
    if (store.paymentMethod === 'ONLINE' && !store.paymentGateway) {
      Alert.alert('Select Gateway', 'Please choose a payment gateway.');
      return;
    }
    navigation.navigate('Confirmation');
  }, [navigation, store.paymentMethod, store.paymentGateway]);

  return (
    <View style={styles.container}>
      <StepIndicator currentStep={4} />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* Payment Methods */}
        <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
          How would you like to pay?
        </Text>

        {PAYMENT_METHODS.map((pm) => {
          const selected = store.paymentMethod === pm.value;
          return (
            <TouchableOpacity
              key={pm.value}
              style={[styles.optionCard, selected && styles.optionSelected]}
              onPress={() => handleSelectMethod(pm.value)}
              activeOpacity={0.7}
            >
              <View style={styles.radioOuter}>
                {selected && <View style={styles.radioInner} />}
              </View>
              <View style={styles.optionText}>
                <Text style={[typography.bodyMedium, { color: '#09090B' }]}>{pm.label}</Text>
                <Text style={[typography.caption, { color: '#71717A' }]}>{pm.desc}</Text>
              </View>
            </TouchableOpacity>
          );
        })}

        {/* Payment Gateways (only if ONLINE selected) */}
        {store.paymentMethod === 'ONLINE' && (
          <View style={styles.gatewaySection}>
            <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
              Select Payment Gateway
            </Text>

            {GATEWAYS.map((gw) => {
              const selected = store.paymentGateway === gw.value;
              return (
                <TouchableOpacity
                  key={gw.value}
                  style={[styles.optionCard, selected && styles.optionSelected]}
                  onPress={() => handleSelectGateway(gw.value)}
                  activeOpacity={0.7}
                >
                  <View style={styles.radioOuter}>
                    {selected && <View style={styles.radioInner} />}
                  </View>
                  <View style={styles.optionText}>
                    <Text style={[typography.bodyMedium, { color: '#09090B' }]}>{gw.label}</Text>
                    <Text style={[typography.caption, { color: '#71717A' }]}>{gw.desc}</Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {/* Price Summary */}
        <PriceSummary
          price={store.quotePrice}
          currency={store.quoteCurrency}
          paxCount={store.paxCount}
          extras={store.extras}
        />

        {/* Confirm Button */}
        <View style={styles.buttonContainer}>
          <Button
            title="Confirm Booking"
            onPress={handleConfirm}
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
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: '#E4E4E7',
    backgroundColor: '#FFFFFF',
    marginBottom: spacing[3],
  },
  optionSelected: {
    borderColor: BLUE_PRIMARY,
    backgroundColor: BLUE_LIGHT,
    borderWidth: 2,
  },
  radioOuter: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: BLUE_PRIMARY,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing[3],
  },
  radioInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: BLUE_PRIMARY,
  },
  optionText: {
    flex: 1,
  },
  gatewaySection: {
    marginTop: spacing[5],
  },
  buttonContainer: {
    marginTop: spacing[8],
  },
});
