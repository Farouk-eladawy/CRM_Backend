import { useState, useCallback } from 'react';
import Geolocation from '@react-native-community/geolocation';
import { Platform, PermissionsAndroid } from 'react-native';

interface GPSPosition {
  lat: number;
  lng: number;
}

export function useGPS() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (Platform.OS === 'ios') return true;

    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      {
        title: 'Location Permission',
        message: 'This app needs access to your location for job tracking.',
        buttonPositive: 'Allow',
        buttonNegative: 'Deny',
      },
    );
    return granted === PermissionsAndroid.RESULTS.GRANTED;
  }, []);

  const captureGPS = useCallback(
    async (timeout = 30000): Promise<GPSPosition> => {
      setLoading(true);
      setError(null);

      const hasPermission = await requestPermission();
      if (!hasPermission) {
        setLoading(false);
        const err = 'Location permission denied. Please enable GPS access.';
        setError(err);
        throw new Error(err);
      }

      const getPosition = (options: {
        enableHighAccuracy: boolean;
        timeout: number;
        maximumAge: number;
      }): Promise<GPSPosition> =>
        new Promise((resolve, reject) => {
          Geolocation.getCurrentPosition(
            (position) =>
              resolve({
                lat: position.coords.latitude,
                lng: position.coords.longitude,
              }),
            (err) => reject(err),
            options,
          );
        });

      const mapError = (positionError: any): string => {
        switch (positionError?.code) {
          case 1:
            return 'Location permission denied. Please enable GPS access.';
          case 2:
            return 'Location unavailable. Please check your GPS settings.';
          case 3:
            return 'Location request timed out. Please try again later.';
          default:
            return 'Unable to get location';
        }
      };

      try {
        // Stage 1: high-accuracy GPS
        const position = await getPosition({
          enableHighAccuracy: true,
          timeout,
          maximumAge: 30000,
        });
        setLoading(false);
        return position;
      } catch (e: any) {
        if (e?.code !== 3) {
          setLoading(false);
          const msg = mapError(e);
          setError(msg);
          throw new Error(msg);
        }
      }

      // Stage 2: network/WiFi fallback
      try {
        const position = await getPosition({
          enableHighAccuracy: false,
          timeout: 10000,
          maximumAge: 60000,
        });
        setLoading(false);
        return position;
      } catch (e: any) {
        setLoading(false);
        const msg = mapError(e);
        setError(msg);
        throw new Error(msg);
      }
    },
    [requestPermission],
  );

  return { captureGPS, loading, error };
}
