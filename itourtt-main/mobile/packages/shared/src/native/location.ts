import { Platform, PermissionsAndroid } from 'react-native';
import Geolocation from '@react-native-community/geolocation';

export interface GPSPosition {
  lat: number;
  lng: number;
  accuracy?: number;
  timestamp: number;
}

/**
 * Request fine location permission.
 */
export async function requestLocationPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;

  const granted = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
    {
      title: 'Location Permission',
      message: 'This app needs location access for job tracking and evidence.',
      buttonPositive: 'Allow',
      buttonNegative: 'Deny',
    },
  );
  return granted === PermissionsAndroid.RESULTS.GRANTED;
}

/**
 * Get current GPS position (one-shot).
 * Stage 1: high-accuracy GPS (30s). Stage 2: network/WiFi fallback (10s).
 * Handles Android cold-start delays on budget devices.
 */
export async function getCurrentPosition(timeout = 30000): Promise<GPSPosition> {
  const hasPermission = await requestLocationPermission();
  if (!hasPermission) {
    throw new Error('Location permission denied');
  }

  try {
    return await _getPosition({ enableHighAccuracy: true, timeout, maximumAge: 30000 });
  } catch (error: any) {
    // Only fall back on timeout; propagate permission/unavailable errors immediately
    if (error?.code !== 3) {
      throw _mapPositionError(error);
    }
  }

  // Stage 2: network/WiFi location — faster fix, lower accuracy
  try {
    return await _getPosition({ enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 });
  } catch (error: any) {
    throw _mapPositionError(error);
  }
}

function _getPosition(options: {
  enableHighAccuracy: boolean;
  timeout: number;
  maximumAge: number;
}): Promise<GPSPosition> {
  return new Promise((resolve, reject) => {
    Geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp,
        });
      },
      (error) => reject(error),
      options,
    );
  });
}

function _mapPositionError(error: any): Error {
  switch (error?.code) {
    case 1:
      return new Error('Location permission denied. Please enable GPS access.');
    case 2:
      return new Error('Location unavailable. Please check your GPS settings.');
    case 3:
      return new Error('Location request timed out. Please try again later.');
    default:
      return new Error('Unable to get location');
  }
}

/**
 * Watch position continuously. Returns a cleanup function to stop watching.
 * Useful for real-time driver location tracking during active trips.
 */
export function watchPosition(
  onPosition: (pos: GPSPosition) => void,
  onError?: (error: Error) => void,
  interval = 10000,
): () => void {
  const watchId = Geolocation.watchPosition(
    (position) => {
      onPosition({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
      });
    },
    (error) => {
      onError?.(new Error(error.message));
    },
    {
      enableHighAccuracy: true,
      distanceFilter: 50, // meters between updates
      interval,
      fastestInterval: 5000,
    },
  );

  return () => Geolocation.clearWatch(watchId);
}

/**
 * Generate a Google Maps link for a GPS position.
 */
export function getMapLink(lat: number, lng: number): string {
  return `https://www.google.com/maps?q=${lat},${lng}`;
}
