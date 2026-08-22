import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet, Alert } from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  publicApi,
  spacing,
  borderRadius,
  typography,
  type GuestBooking,
  type GuestBookingStatus,
} from '@itour/shared';
import { Button, LoadingSpinner, ErrorBanner, Badge } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';

type Route = RouteProp<RootStackParamList, 'BookingDetail'>;
type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';

const STATUS_COLORS: Record<GuestBookingStatus, { bg: string; text: string; border: string }> = {
  CONFIRMED: { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' },
  CANCELLED: { bg: '#F4F4F5', text: '#71717A', border: '#D4D4D8' },
  CONVERTED: { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' },
};

export function BookingDetailScreen() {
  const route = useRoute<Route>();
  const navigation = useNavigation<Nav>();
  const { bookingRef, email } = route.params;

  const [booking, setBooking] = useState<GuestBooking | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const fetchBooking = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: resData } = await publicApi.getBooking(bookingRef, email);
      const bk = (resData as any)?.data ?? resData;
      setBooking(bk as GuestBooking);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Failed to load booking.');
    } finally {
      setLoading(false);
    }
  }, [bookingRef, email]);

  useEffect(() => {
    fetchBooking();
  }, [fetchBooking]);

  const handleCancel = useCallback(() => {
    Alert.alert(
      'Cancel Booking',
      'Are you sure you want to cancel this booking? This action cannot be undone.',
      [
        { text: 'Keep Booking', style: 'cancel' },
        {
          text: 'Cancel Booking',
          style: 'destructive',
          onPress: async () => {
            setCancelling(true);
            try {
              await publicApi.cancelBooking(bookingRef, email);
              Alert.alert('Cancelled', 'Your booking has been cancelled.');
              fetchBooking();
            } catch (err: any) {
              Alert.alert(
                'Error',
                err?.response?.data?.message || err?.message || 'Failed to cancel.',
              );
            } finally {
              setCancelling(false);
            }
          },
        },
      ],
    );
  }, [bookingRef, email, fetchBooking]);

  if (loading) {
    return (
      <View style={styles.container}>
        <LoadingSpinner fullScreen message="Loading booking details..." />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <View style={styles.centered}>
          <ErrorBanner message={error} onRetry={fetchBooking} />
        </View>
      </View>
    );
  }

  if (!booking) return null;

  const statusColor = STATUS_COLORS[booking.status] || STATUS_COLORS.CONFIRMED;
  const canCancel = booking.status === 'CONFIRMED';

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Status & Reference */}
        <View style={styles.headerCard}>
          <Badge
            label={booking.status}
            backgroundColor={statusColor.bg}
            textColor={statusColor.text}
            borderColor={statusColor.border}
          />
          <Text style={[typography.h3, { color: '#09090B', marginTop: spacing[2] }]}>
            {booking.bookingRef}
          </Text>
          <Text style={[typography.bodySm, { color: '#71717A', marginTop: spacing[1] }]}>
            Booked on {new Date(booking.createdAt).toLocaleDateString()}
          </Text>
        </View>

        {/* Transfer Details */}
        <View style={styles.section}>
          <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
            Transfer Details
          </Text>
          <DetailRow label="Service" value={booking.serviceType === 'ARR' ? 'Arrival' : 'Departure'} />
          <DetailRow label="Date" value={booking.jobDate} />
          {booking.pickupTime && <DetailRow label="Time" value={booking.pickupTime} />}
          <DetailRow label="Passengers" value={String(booking.paxCount)} />

          {booking.originAirport && (
            <DetailRow
              label="Airport"
              value={`${booking.originAirport.name} (${booking.originAirport.code})`}
            />
          )}
          {booking.destinationAirport && (
            <DetailRow
              label="Airport"
              value={`${booking.destinationAirport.name} (${booking.destinationAirport.code})`}
            />
          )}
          {booking.originZone && <DetailRow label="Pickup Zone" value={booking.originZone.name} />}
          {booking.destinationZone && (
            <DetailRow label="Drop-off Zone" value={booking.destinationZone.name} />
          )}
          {booking.originHotel && <DetailRow label="Hotel" value={booking.originHotel.name} />}
          {booking.destinationHotel && (
            <DetailRow label="Hotel" value={booking.destinationHotel.name} />
          )}
          {booking.vehicleType && (
            <DetailRow label="Vehicle" value={booking.vehicleType.name} />
          )}
        </View>

        {/* Guest Details */}
        <View style={styles.section}>
          <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
            Guest Details
          </Text>
          <DetailRow label="Name" value={booking.guestName} />
          <DetailRow label="Email" value={booking.guestEmail} />
          <DetailRow label="Phone" value={booking.guestPhone} />
        </View>

        {/* Payment */}
        <View style={styles.section}>
          <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
            Payment
          </Text>
          <DetailRow
            label="Method"
            value={booking.paymentMethod === 'PAY_ON_ARRIVAL' ? 'Pay on Arrival' : 'Online'}
          />
          <DetailRow label="Status" value={booking.paymentStatus} />
          <DetailRow
            label="Total"
            value={`${booking.currency} ${booking.price.toFixed(2)}`}
            bold
          />
        </View>

        {/* Cancel Button */}
        {canCancel && (
          <View style={styles.cancelContainer}>
            <Button
              title="Cancel Booking"
              onPress={handleCancel}
              variant="destructive"
              size="lg"
              loading={cancelling}
            />
          </View>
        )}

        {/* Go Home */}
        <View style={styles.homeContainer}>
          <Button
            title="Back to Home"
            onPress={() => navigation.reset({ index: 0, routes: [{ name: 'Home' }] })}
            variant="outline"
            size="md"
          />
        </View>
      </ScrollView>
    </View>
  );
}

function DetailRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <View style={detailStyles.row}>
      <Text style={[typography.bodySm, { color: '#71717A', flex: 1 }]}>{label}</Text>
      <Text
        style={[
          bold ? typography.bodyMedium : typography.bodySmMedium,
          { color: '#09090B', flex: 2, textAlign: 'right' },
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

const detailStyles = StyleSheet.create({
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
  centered: {
    flex: 1,
    justifyContent: 'center',
  },
  scrollContent: {
    padding: spacing[5],
    paddingBottom: spacing[10],
  },
  headerCard: {
    alignItems: 'center',
    padding: spacing[5],
    borderRadius: borderRadius.xl,
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#E4E4E7',
  },
  section: {
    marginTop: spacing[6],
    padding: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: '#E4E4E7',
    backgroundColor: '#FFFFFF',
  },
  cancelContainer: {
    marginTop: spacing[8],
  },
  homeContainer: {
    marginTop: spacing[3],
    alignItems: 'center',
  },
});
