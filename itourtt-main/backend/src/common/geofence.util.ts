/**
 * Haversine distance calculation and geofence utilities.
 */

const EARTH_RADIUS_METERS = 6_371_000;

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

/** Returns distance in meters between two lat/lng points using the Haversine formula. */
export function haversineDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_METERS * c;
}

/** Returns true if the point (lat1, lng1) is within `radiusMeters` of (lat2, lng2). */
export function isWithinGeofence(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
  radiusMeters = 500,
): boolean {
  return haversineDistance(lat1, lng1, lat2, lng2) <= radiusMeters;
}

interface GeofenceLocation {
  latitude?: unknown;
  longitude?: unknown;
}

interface GeofenceJob {
  serviceType: string;
  originAirport?: GeofenceLocation | null;
  originHotel?: (GeofenceLocation & { zone?: GeofenceLocation | null }) | null;
  originZone?: GeofenceLocation | null;
  destinationAirport?: GeofenceLocation | null;
  destinationHotel?: (GeofenceLocation & { zone?: GeofenceLocation | null }) | null;
  destinationZone?: GeofenceLocation | null;
}

function toCoord(loc: GeofenceLocation | null | undefined): { lat: number; lng: number } | null {
  if (!loc) return null;
  const lat = Number(loc.latitude);
  const lng = Number(loc.longitude);
  if (isNaN(lat) || isNaN(lng) || lat === 0 || lng === 0) return null;
  return { lat, lng };
}

/**
 * Resolves the geofence target coordinate for a rep.
 * Reps are always at the airport.
 */
export function resolveRepGeofenceTarget(job: GeofenceJob): { lat: number; lng: number } | null {
  return toCoord(job.originAirport);
}

/**
 * Resolves the geofence target coordinate for a driver.
 * - ARR jobs: driver goes to the airport
 * - DEP/CITY jobs: driver goes to the origin hotel/zone
 */
export function resolveDriverGeofenceTarget(job: GeofenceJob): { lat: number; lng: number } | null {
  if (job.serviceType === 'ARR') {
    return toCoord(job.originAirport);
  }

  // DEP or CITY: origin hotel → origin zone → origin hotel's zone
  const hotelCoord = toCoord(job.originHotel);
  if (hotelCoord) return hotelCoord;

  const zoneCoord = toCoord(job.originZone);
  if (zoneCoord) return zoneCoord;

  // Fallback: hotel's parent zone
  if (job.originHotel?.zone) {
    return toCoord(job.originHotel.zone);
  }

  return null;
}
