import { Injectable, Logger } from '@nestjs/common';
import { SettingsService } from '../settings/settings.service.js';

export interface PlaceResult {
  placeId: string;
  name: string;
  formattedAddress: string;
  lat: number;
  lng: number;
}

@Injectable()
export class GeocodingService {
  private readonly logger = new Logger(GeocodingService.name);

  constructor(private readonly settings: SettingsService) {}

  private async getApiKey(): Promise<string> {
    const s = await this.settings.getSystemSettings();
    const key = (s as any).googleMapsApiKey;
    if (!key) {
      throw new Error('Google Maps API key not configured. Set it in Settings > System.');
    }
    return key;
  }

  /**
   * Search for places using the (new) Google Places API — Text Search.
   *
   * The legacy `maps/api/place/textsearch/json` endpoint now returns
   * REQUEST_DENIED for this Cloud project (Google retired the legacy Places
   * API), so we call `places.googleapis.com/v1/places:searchText` instead.
   */
  async searchPlaces(query: string, type?: string): Promise<PlaceResult[]> {
    const apiKey = await this.getApiKey();

    // Map our location types to the new Places API `includedType` where a
    // valid (Table A) place type exists. country/zone have no usable bias type,
    // so we leave the search unfiltered for those.
    const typeMap: Record<string, string> = {
      airport: 'airport',
      city: 'locality',
      hotel: 'lodging',
    };

    const body: Record<string, unknown> = { textQuery: query };
    if (type && typeMap[type]) {
      body.includedType = typeMap[type];
    }

    const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': apiKey,
        'X-Goog-FieldMask':
          'places.id,places.displayName,places.formattedAddress,places.location',
      },
      body: JSON.stringify(body),
    });
    const data = await response.json();

    if (!response.ok) {
      this.logger.warn(
        `Google Places API error: ${response.status} - ${data?.error?.message || ''}`,
      );
      return [];
    }

    return (data.places || []).slice(0, 10).map((r: any) => ({
      placeId: r.id,
      name: r.displayName?.text || r.formattedAddress || '',
      formattedAddress: r.formattedAddress || '',
      lat: r.location?.latitude,
      lng: r.location?.longitude,
    }));
  }

  /**
   * Geocode an address string to coordinates using Google Geocoding API.
   */
  async geocodeAddress(query: string): Promise<PlaceResult[]> {
    const apiKey = await this.getApiKey();

    const params = new URLSearchParams({
      address: query,
      key: apiKey,
    });

    const url = `https://maps.googleapis.com/maps/api/geocode/json?${params.toString()}`;
    const response = await fetch(url);
    const data = await response.json();

    if (data.status !== 'OK' && data.status !== 'ZERO_RESULTS') {
      this.logger.warn(`Google Geocoding API error: ${data.status} - ${data.error_message || ''}`);
      return [];
    }

    return (data.results || []).slice(0, 5).map((r: any) => ({
      placeId: r.place_id,
      name: r.formatted_address,
      formattedAddress: r.formatted_address,
      lat: r.geometry.location.lat,
      lng: r.geometry.location.lng,
    }));
  }
}
