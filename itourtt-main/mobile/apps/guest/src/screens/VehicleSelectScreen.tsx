import React, { useEffect, useState, useCallback } from 'react';
import { View, ScrollView, Text, StyleSheet, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  publicApi,
  spacing,
  typography,
  type VehicleType,
  type QuoteRequest,
  type ServiceType,
} from '@itour/shared';
import { Button, LoadingSpinner, ErrorBanner } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { useBookingStore } from '../stores/booking-store';
import { StepIndicator } from '../components/StepIndicator';
import { VehicleTypeCard } from '../components/VehicleTypeCard';
import { ExtrasSelector } from '../components/ExtrasSelector';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';

interface VehicleQuote {
  vehicleType: VehicleType;
  price: number | null;
  currency: string;
  breakdown: Record<string, unknown> | null;
  loading: boolean;
}

export function VehicleSelectScreen() {
  const navigation = useNavigation<Nav>();
  const store = useBookingStore();

  const [vehicleQuotes, setVehicleQuotes] = useState<VehicleQuote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVehicleTypesAndQuotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: vtData } = await publicApi.getVehicleTypes();
      const vehicleTypes: VehicleType[] = Array.isArray(vtData) ? vtData : (vtData as any)?.data ?? [];

      // Initialize with loading state
      const initialQuotes: VehicleQuote[] = vehicleTypes.map((vt) => ({
        vehicleType: vt,
        price: null,
        currency: 'USD',
        breakdown: null,
        loading: true,
      }));
      setVehicleQuotes(initialQuotes);
      setLoading(false);

      // Fetch quotes for each vehicle type
      const quotePromises = vehicleTypes.map(async (vt) => {
        try {
          const quoteReq: QuoteRequest = {
            serviceType: store.serviceType as ServiceType,
            originAirportId: store.originAirportId || undefined,
            originZoneId: store.fromZoneId || undefined,
            originHotelId: undefined,
            destinationAirportId: store.destinationAirportId || undefined,
            destinationZoneId: store.toZoneId || undefined,
            destinationHotelId: store.hotelId || undefined,
            vehicleTypeId: vt.id,
            paxCount: store.paxCount,
          };
          const { data: qData } = await publicApi.getQuote(quoteReq);
          const quote = (qData as any)?.data ?? qData;
          return {
            vehicleType: vt,
            price: quote.price,
            currency: quote.currency,
            breakdown: quote.breakdown ?? null,
            loading: false,
          };
        } catch {
          return {
            vehicleType: vt,
            price: null,
            currency: 'USD',
            breakdown: null,
            loading: false,
          };
        }
      });

      const results = await Promise.all(quotePromises);
      setVehicleQuotes(results);
    } catch (err: any) {
      setError(err?.message || 'Failed to load vehicle types');
      setLoading(false);
    }
  }, [store.serviceType, store.originAirportId, store.fromZoneId, store.destinationAirportId, store.toZoneId, store.hotelId, store.paxCount]);

  useEffect(() => {
    fetchVehicleTypesAndQuotes();
  }, [fetchVehicleTypesAndQuotes]);

  const handleSelectVehicle = useCallback(
    (vq: VehicleQuote) => {
      if (vq.price === null) {
        Alert.alert('Unavailable', 'No pricing available for this vehicle type.');
        return;
      }
      store.setField('vehicleTypeId', vq.vehicleType.id);
      store.setQuote(vq.price, vq.currency, vq.breakdown);
    },
    [store],
  );

  const handleNext = () => {
    if (!store.vehicleTypeId) {
      Alert.alert('Select Vehicle', 'Please choose a vehicle type to continue.');
      return;
    }
    navigation.navigate('GuestDetails');
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <StepIndicator currentStep={2} />
        <LoadingSpinner fullScreen message="Loading vehicles..." />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StepIndicator currentStep={2} />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {error && <ErrorBanner message={error} onRetry={fetchVehicleTypesAndQuotes} />}

        <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[3] }]}>
          Select Vehicle Type
        </Text>

        {vehicleQuotes.map((vq) => (
          <VehicleTypeCard
            key={vq.vehicleType.id}
            vehicleType={vq.vehicleType}
            price={vq.price}
            currency={vq.currency}
            loading={vq.loading}
            selected={store.vehicleTypeId === vq.vehicleType.id}
            onSelect={() => handleSelectVehicle(vq)}
          />
        ))}

        {/* Extras */}
        <ExtrasSelector
          extras={store.extras}
          onChangeExtra={(key, value) => store.setExtra(key, value)}
        />

        {/* Next Button */}
        <View style={styles.buttonContainer}>
          <Button
            title="Enter Your Details"
            onPress={handleNext}
            variant="primary"
            size="lg"
            disabled={!store.vehicleTypeId}
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
