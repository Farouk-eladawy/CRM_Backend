import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { HomeScreen } from '../screens/HomeScreen';
import { SearchScreen } from '../screens/SearchScreen';
import { VehicleSelectScreen } from '../screens/VehicleSelectScreen';
import { GuestDetailsScreen } from '../screens/GuestDetailsScreen';
import { PaymentScreen } from '../screens/PaymentScreen';
import { ConfirmationScreen } from '../screens/ConfirmationScreen';
import { BookingLookupScreen } from '../screens/BookingLookupScreen';
import { BookingDetailScreen } from '../screens/BookingDetailScreen';

export type RootStackParamList = {
  Home: undefined;
  Search: undefined;
  VehicleSelect: undefined;
  GuestDetails: undefined;
  Payment: undefined;
  Confirmation: undefined;
  BookingLookup: undefined;
  BookingDetail: { bookingRef: string; email: string };
};

const Stack = createStackNavigator<RootStackParamList>();

/** Blue accent used for header tint */
const HEADER_TINT = '#1D4ED8';

export function RootNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: true,
        headerTintColor: HEADER_TINT,
        headerTitleStyle: { color: '#09090B', fontWeight: '600' },
        headerStyle: { backgroundColor: '#FFFFFF', elevation: 0, shadowOpacity: 0 },
      }}
    >
      <Stack.Screen
        name="Home"
        component={HomeScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="Search"
        component={SearchScreen}
        options={{ title: 'Transfer Details' }}
      />
      <Stack.Screen
        name="VehicleSelect"
        component={VehicleSelectScreen}
        options={{ title: 'Choose Vehicle' }}
      />
      <Stack.Screen
        name="GuestDetails"
        component={GuestDetailsScreen}
        options={{ title: 'Your Details' }}
      />
      <Stack.Screen
        name="Payment"
        component={PaymentScreen}
        options={{ title: 'Payment' }}
      />
      <Stack.Screen
        name="Confirmation"
        component={ConfirmationScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="BookingLookup"
        component={BookingLookupScreen}
        options={{ title: 'Track Booking' }}
      />
      <Stack.Screen
        name="BookingDetail"
        component={BookingDetailScreen}
        options={{ title: 'Booking Details' }}
      />
    </Stack.Navigator>
  );
}
