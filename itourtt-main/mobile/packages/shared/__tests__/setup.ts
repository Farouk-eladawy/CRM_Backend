// Mock react-native modules
jest.mock('react-native/Libraries/Animated/NativeAnimatedHelper');
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Platform: { OS: 'android', select: jest.fn((obj: any) => obj.android) },
    Alert: { alert: jest.fn() },
    Linking: { openURL: jest.fn(), canOpenURL: jest.fn().mockResolvedValue(true) },
    PermissionsAndroid: {
      request: jest.fn().mockResolvedValue('granted'),
      PERMISSIONS: { ACCESS_FINE_LOCATION: 'android.permission.ACCESS_FINE_LOCATION', CAMERA: 'android.permission.CAMERA' },
      RESULTS: { GRANTED: 'granted' },
    },
    Appearance: { getColorScheme: jest.fn(() => 'light'), addChangeListener: jest.fn(() => ({ remove: jest.fn() })) },
  };
});
