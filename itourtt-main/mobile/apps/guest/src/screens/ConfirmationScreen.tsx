import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  publicApi,
  spacing,
  borderRadius,
  typography,
  type CreateGuestBooking,
  type ServiceType,
  type B2CPaymentMethod,
  type B2CPaymentGateway,
} from '@itour/shared';
import { Button, LoadingSpinner, ErrorBanner } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { useBookingStore } from '../stores/booking-store';
import { StepIndicator } from '../components/StepIndicator';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';
const GREEN_SUCCESS = '#16A34A';

export function ConfirmationScreen() {
  const navigation = useNavigation<Nav>();
  const store = useBookingStore();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bookingRef, setBookingRef] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const submitBooking = useCallback(async () => {
    if (submitted) return;
    setSubmitted(true);
    setLoading(true);
    setError(null);

    try {
      const payload: CreateGuestBooking = {
        serviceType: store.serviceType as ServiceType,
        vehicleTypeId: store.vehicleTypeId,
        jobDate: store.jobDate,
        paxCount: store.paxCount,
        guestName: store.guestName.trim(),
        guestEmail: store.guestEmail.trim(),
        guestPhone: store.guestPhone.trim(),
        paymentMethod: store.paymentMethod as B2CPaymentMethod,
      };

      // Conditional fields
      if (store.originAirportId) payload.originAirportId = store.originAirportId;
      if (store.fromZoneId) payload.originZoneId = store.fromZoneId;
      if (store.destinationAirportId) payload.destinationAirportId = store.destinationAirportId;
      if (store.toZoneId) payload.destinationZoneId = store.toZoneId;
      if (store.hotelId) payload.destinationHotelId = store.hotelId;
      if (store.pickupTime) payload.pickupTime = store.pickupTime;
      if (store.guestCountry) payload.guestCountry = store.guestCountry.trim();
      if (store.flightNo) payload.flightNo = store.flightNo.trim();
      if (store.carrier) payload.carrier = store.carrier.trim();
      if (store.terminal) payload.terminal = store.terminal.trim();
      if (store.notes) payload.notes = store.notes.trim();

      const hasExtras =
        store.extras.babySeatQty > 0 ||
        store.extras.boosterSeatQty > 0 ||
        store.extras.wheelChairQty > 0;
      if (hasExtras) payload.extras = store.extras;

      if (store.paymentMethod === 'ONLINE' && store.paymentGateway) {
        payload.paymentGateway = store.paymentGateway as B2CPaymentGateway;
      }

      const { data: resData } = await publicApi.createBooking(payload);
      const booking = (resData as any)?.data ?? resData;
      const ref = booking.bookingRef || booking.id;
      setBookingRef(ref);
      store.setField('bookingRef', ref);
    } catch (err: any) {
      const msg =
        err?.response?.data?.message || err?.message || 'Failed to create booking.';
      setError(msg);
      setSubmitted(false);
    } finally {
      setLoading(false);
    }
  }, [store, submitted]);

  useEffect(() => {
    submitBooking();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleGoHome = () => {
    store.reset();
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  };

  const handleViewBooking = () => {
    if (bookingRef) {
      navigation.reset({
        index: 1,
        routes: [{ name: 'Home' }, { name: 'BookingDetail', params: { bookingRef } }],
      });
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <StepIndicator currentStep={5} />
        <LoadingSpinner fullScreen message="Submitting your booking..." />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <StepIndicator currentStep={5} />
        <View style={styles.centeredContent}>
          <ErrorBanner message={error} />
          <View style={styles.retryContainer}>
            <Button
              title="Try Again"
              onPress={() => {
                setError(null);
                setSubmitted(false);
                submitBooking();
              }}
              variant="primary"
              style={{ backgroundColor: BLUE_PRIMARY }}
            />
            <Button
              title="Go Back"
              onPress={() => navigation.goBack()}
              variant="outline"
              style={{ marginTop: spacing[3] }}
            />
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StepIndicator currentStep={5} />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Success Icon */}
        <View style={styles.successIcon}>
          <Text style={styles.successCheck}>{'✓'}</Text>
        </View>

        <Text style={[typography.h2, { color: '#09090B', textAlign: 'center' }]}>
          Booking Confirmed!
        </Text>
        <Text
          style={[
            typography.body,
            { color: '#71717A', textAlign: 'center', marginTop: spacing[2] },
          ]}
        >
          Your transfer has been booked successfully.
        </Text>

        {/* Booking Reference */}
        <View style={styles.refCard}>
          <Text style={[typography.bodySm, { color: '#71717A' }]}>Booking Reference</Text>
          <Text style={[typography.h2, { color: BLUE_PRIMARY, marginTop: spacing[1] }]}>
            {bookingRef}
          </Text>
          <Text style={[typography.caption, { color: '#A1A1AA', marginTop: spacing[2] }]}>
            Save this reference to track your booking
          </Text>
        </View>

        {/* Summary */}
        <View style={styles.summaryCard}>
          <SummaryRow label="Service" value={store.serviceType === 'ARR' ? 'Arrival' : 'Departure'} />
          <SummaryRow label="Date" value={store.jobDate} />
          {store.pickupTime && <SummaryRow label="Time" value={store.pickupTime} />}
          <SummaryRow label="Passengers" value={String(store.paxCount)} />
          <SummaryRow label="Guest" value={store.guestName} />
          <SummaryRow label="Email" value={store.guestEmail} />
          <SummaryRow
            label="Payment"
            value={store.paymentMethod === 'PAY_ON_ARRIVAL' ? 'Pay on Arrival' : 'Online'}
          />
          {store.quotePrice !== null && (
            <SummaryRow
              label="Total"
              value={`${store.quoteCurrency} ${store.quotePrice.toFixed(2)}`}
              bold
            />
          )}
        </View>

        {/* Actions */}
        <View style={styles.actionsContainer}>
          <Button
            title="View Booking Details"
            onPress={handleViewBooking}
            variant="primary"
            size="lg"
            style={{ backgroundColor: BLUE_PRIMARY }}
          />
          <Button
            title="Back to Home"
            onPress={handleGoHome}
            variant="outline"
            size="lg"
            style={{ marginTop: spacing[3] }}
          />
        </View>
      </ScrollView>
    </View>
  );
}

function SummaryRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <View style={summaryStyles.row}>
      <Text style={[typography.bodySm, { color: '#71717A' }]}>{label}</Text>
      <Text style={[bold ? typography.bodyMedium : typography.bodySmMedium, { color: '#09090B' }]}>
        {value}
      </Text>
    </View>
  );
}

const summaryStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing[1.5],
  },
});

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  centeredContent: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing[5],
  },
  retryContainer: {
    marginTop: spacing[6],
    paddingHorizontal: spacing[4],
  },
  scrollContent: {
    padding: spacing[5],
    paddingBottom: spacing[10],
    alignItems: 'center',
  },
  successIcon: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: GREEN_SUCCESS,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing[5],
    marginTop: spacing[4],
  },
  successCheck: {
    color: '#FFFFFF',
    fontSize: 36,
    fontWeight: '700',
  },
  refCard: {
    alignItems: 'center',
    padding: spacing[5],
    borderRadius: borderRadius.xl,
    backgroundColor: '#EFF6FF',
    borderWidth: 1,
    borderColor: '#BFDBFE',
    marginTop: spacing[6],
    width: '100%',
  },
  summaryCard: {
    padding: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: '#E4E4E7',
    backgroundColor: '#F9FAFB',
    marginTop: spacing[5],
    width: '100%',
  },
  actionsContainer: {
    marginTop: spacing[8],
    width: '100%',
  },
});
