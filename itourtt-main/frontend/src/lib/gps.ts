// Grace period for acquiring a fix. GPS is mandatory for evidence, so the
// high-accuracy attempt gets a long window (cold GPS fixes outdoors can take a
// while) before falling back to the faster network/WiFi lookup.
export function captureGPS(timeout = 60000): Promise<{ lat: number; lng: number }> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation is not supported by this browser"));
      return;
    }

    // Stage 1: high-accuracy GPS
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
      },
      (error) => {
        // Only fall back on timeout; propagate permission/unavailable errors immediately
        if (error.code !== error.TIMEOUT) {
          reject(_mapError(error));
          return;
        }

        // Stage 2: network/WiFi fallback (faster, works indoors)
        navigator.geolocation.getCurrentPosition(
          (position) => {
            resolve({
              lat: position.coords.latitude,
              lng: position.coords.longitude,
            });
          },
          (fallbackError) => reject(_mapError(fallbackError)),
          { enableHighAccuracy: false, timeout: 30000, maximumAge: 60000 },
        );
      },
      { enableHighAccuracy: true, timeout, maximumAge: 30000 },
    );
  });
}

/** Error thrown by captureGPS, carrying the underlying GeolocationPositionError code. */
export interface GeoError extends Error {
  /** GeolocationPositionError code: 1=PERMISSION_DENIED, 2=POSITION_UNAVAILABLE, 3=TIMEOUT */
  code?: number;
}

function _mapError(error: GeolocationPositionError): GeoError {
  let err: GeoError;
  switch (error.code) {
    case error.PERMISSION_DENIED:
      err = new Error("Location permission denied. Please enable GPS access.");
      break;
    case error.POSITION_UNAVAILABLE:
      err = new Error("Location unavailable. Please check your GPS settings.");
      break;
    case error.TIMEOUT:
      err = new Error("Location request timed out. Please try again later.");
      break;
    default:
      err = new Error("Unable to get location");
  }
  err.code = error.code;
  return err;
}
