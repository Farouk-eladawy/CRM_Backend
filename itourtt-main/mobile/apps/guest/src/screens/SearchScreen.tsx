import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Platform,
  StyleSheet,
  Alert,
} from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { spacing, borderRadius, typography, type ServiceType } from '@itour/shared';
import { Button } from '@itour/ui';
import type { RootStackParamList } from '../navigation/RootNavigator';
import { useBookingStore } from '../stores/booking-store';
import { StepIndicator } from '../components/StepIndicator';
import { LocationPicker } from '../components/LocationPicker';

type Nav = StackNavigationProp<RootStackParamList>;

const BLUE_PRIMARY = '#1D4ED8';
const BLUE_LIGHT = '#EFF6FF';

const SERVICE_TYPES: { value: ServiceType; label: string; desc: string }[] = [
  { value: 'ARR', label: 'Arrival', desc: 'Airport to hotel' },
  { value: 'DEP', label: 'Departure', desc: 'Hotel to airport' },
];

export function SearchScreen() {
  const navigation = useNavigation<Nav>();
  const store = useBookingStore();

  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);

  const dateValue = store.jobDate ? new Date(store.jobDate) : new Date();
  const timeValue = store.pickupTime
    ? (() => {
        const [h, m] = store.pickupTime.split(':').map(Number);
        const d = new Date();
        d.setHours(h, m, 0, 0);
        return d;
      })()
    : new Date();

  const handleDateChange = useCallback(
    (_: unknown, selected?: Date) => {
      setShowDatePicker(Platform.OS === 'ios');
      if (selected) {
        const iso = selected.toISOString().split('T')[0];
        store.setField('jobDate', iso);
      }
    },
    [store],
  );

  const handleTimeChange = useCallback(
    (_: unknown, selected?: Date) => {
      setShowTimePicker(Platform.OS === 'ios');
      if (selected) {
        const hh = String(selected.getHours()).padStart(2, '0');
        const mm = String(selected.getMinutes()).padStart(2, '0');
        store.setField('pickupTime', `${hh}:${mm}`);
      }
    },
    [store],
  );

  const incrementPax = () => store.setField('paxCount', store.paxCount + 1);
  const decrementPax = () => {
    if (store.paxCount > 1) store.setField('paxCount', store.paxCount - 1);
  };

  const handleNext = () => {
    if (!store.serviceType) {
      Alert.alert('Missing Field', 'Please select a service type.');
      return;
    }
    if (!store.jobDate) {
      Alert.alert('Missing Field', 'Please select a date.');
      return;
    }
    const isArr = store.serviceType === 'ARR';
    if (isArr && !store.originAirportId) {
      Alert.alert('Missing Field', 'Please select an arrival airport.');
      return;
    }
    if (!isArr && !store.destinationAirportId) {
      Alert.alert('Missing Field', 'Please select a departure airport.');
      return;
    }
    if (isArr && !store.toZoneId) {
      Alert.alert('Missing Field', 'Please select a destination zone.');
      return;
    }
    if (!isArr && !store.fromZoneId) {
      Alert.alert('Missing Field', 'Please select a pickup zone.');
      return;
    }
    navigation.navigate('VehicleSelect');
  };

  return (
    <View style={styles.container}>
      <StepIndicator currentStep={1} />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* Service Type */}
        <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[2] }]}>
          Service Type
        </Text>
        <View style={styles.serviceTypeRow}>
          {SERVICE_TYPES.map((st) => {
            const selected = store.serviceType === st.value;
            return (
              <TouchableOpacity
                key={st.value}
                style={[
                  styles.serviceTypeButton,
                  selected && styles.serviceTypeSelected,
                ]}
                onPress={() => {
                  store.setField('serviceType', st.value);
                  // Reset location selections when switching type
                  store.setField('originAirportId', '');
                  store.setField('destinationAirportId', '');
                  store.setField('fromZoneId', '');
                  store.setField('toZoneId', '');
                  store.setField('hotelId', '');
                }}
              >
                <Text
                  style={[
                    typography.bodyMedium,
                    { color: selected ? BLUE_PRIMARY : '#71717A' },
                  ]}
                >
                  {st.label}
                </Text>
                <Text
                  style={[
                    typography.caption,
                    { color: selected ? BLUE_PRIMARY : '#A1A1AA' },
                  ]}
                >
                  {st.desc}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Location Picker */}
        {store.serviceType !== '' && (
          <View style={styles.section}>
            <LocationPicker
              serviceType={store.serviceType}
              originAirportId={store.originAirportId}
              destinationAirportId={store.destinationAirportId}
              fromZoneId={store.fromZoneId}
              toZoneId={store.toZoneId}
              hotelId={store.hotelId}
              onChangeOriginAirport={(id) => store.setField('originAirportId', id)}
              onChangeDestinationAirport={(id) => store.setField('destinationAirportId', id)}
              onChangeFromZone={(id) => store.setField('fromZoneId', id)}
              onChangeToZone={(id) => store.setField('toZoneId', id)}
              onChangeHotel={(id) => store.setField('hotelId', id)}
            />
          </View>
        )}

        {/* Date Picker */}
        <View style={styles.section}>
          <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[1] }]}>
            Date
          </Text>
          <TouchableOpacity
            style={styles.pickerButton}
            onPress={() => setShowDatePicker(true)}
          >
            <Text
              style={[
                typography.body,
                { color: store.jobDate ? '#09090B' : '#71717A' },
              ]}
            >
              {store.jobDate || 'Select date'}
            </Text>
          </TouchableOpacity>
          {showDatePicker && (
            <DateTimePicker
              value={dateValue}
              mode="date"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              minimumDate={new Date()}
              onChange={handleDateChange}
            />
          )}
        </View>

        {/* Time Picker */}
        <View style={styles.section}>
          <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[1] }]}>
            Pickup Time
          </Text>
          <TouchableOpacity
            style={styles.pickerButton}
            onPress={() => setShowTimePicker(true)}
          >
            <Text
              style={[
                typography.body,
                { color: store.pickupTime ? '#09090B' : '#71717A' },
              ]}
            >
              {store.pickupTime || 'Select time (optional)'}
            </Text>
          </TouchableOpacity>
          {showTimePicker && (
            <DateTimePicker
              value={timeValue}
              mode="time"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              onChange={handleTimeChange}
            />
          )}
        </View>

        {/* Pax Count */}
        <View style={styles.section}>
          <Text style={[typography.label, { color: '#09090B', marginBottom: spacing[1] }]}>
            Number of Passengers
          </Text>
          <View style={styles.paxRow}>
            <TouchableOpacity
              style={[styles.paxButton, store.paxCount <= 1 && styles.paxButtonDisabled]}
              onPress={decrementPax}
              disabled={store.paxCount <= 1}
            >
              <Text
                style={[
                  styles.paxButtonText,
                  store.paxCount <= 1 && { color: '#D4D4D8' },
                ]}
              >
                -
              </Text>
            </TouchableOpacity>
            <Text style={[typography.h3, { color: '#09090B', minWidth: 48, textAlign: 'center' }]}>
              {store.paxCount}
            </Text>
            <TouchableOpacity style={styles.paxButton} onPress={incrementPax}>
              <Text style={styles.paxButtonText}>+</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Next Button */}
        <View style={styles.buttonContainer}>
          <Button
            title="Choose Vehicle"
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
  section: {
    marginTop: spacing[5],
  },
  serviceTypeRow: {
    flexDirection: 'row',
    gap: spacing[3],
  },
  serviceTypeButton: {
    flex: 1,
    padding: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: '#E4E4E7',
    alignItems: 'center',
  },
  serviceTypeSelected: {
    borderColor: BLUE_PRIMARY,
    backgroundColor: BLUE_LIGHT,
    borderWidth: 2,
  },
  pickerButton: {
    height: 48,
    borderWidth: 1,
    borderColor: '#E4E4E7',
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing[3],
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  paxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[4],
    marginTop: spacing[2],
  },
  paxButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: BLUE_PRIMARY,
    alignItems: 'center',
    justifyContent: 'center',
  },
  paxButtonDisabled: {
    borderColor: '#D4D4D8',
  },
  paxButtonText: {
    fontSize: 22,
    fontWeight: '600',
    color: BLUE_PRIMARY,
    lineHeight: 24,
  },
  buttonContainer: {
    marginTop: spacing[8],
  },
});
