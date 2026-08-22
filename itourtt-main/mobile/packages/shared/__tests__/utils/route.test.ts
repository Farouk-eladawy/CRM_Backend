import { getOriginLabel, getDestinationLabel, getRouteLabel } from '../../src/utils/route';
import type { PortalJob } from '../../src/types';

// Helper to create a minimal PortalJob for testing
function createJob(overrides: Partial<PortalJob> = {}): PortalJob {
  return {
    id: 'job-1',
    internalRef: 'TF-2026-0001',
    serviceType: 'ARR',
    jobDate: '2026-02-20',
    status: 'PENDING',
    paxCount: 2,
    clientName: null,
    clientMobile: null,
    pickUpTime: null,
    notes: null,
    ...overrides,
  };
}

describe('route utils', () => {
  describe('getOriginLabel', () => {
    it('returns airport name with code when originAirport is set', () => {
      const job = createJob({
        originAirport: { id: 'a1', name: 'Cairo International', code: 'CAI' },
      });
      expect(getOriginLabel(job)).toBe('Cairo International (CAI)');
    });

    it('returns hotel name when originHotel is set (no airport)', () => {
      const job = createJob({
        originHotel: { id: 'h1', name: 'Marriott Mena House' },
      });
      expect(getOriginLabel(job)).toBe('Marriott Mena House');
    });

    it('returns zone name when originZone is set (no airport or hotel)', () => {
      const job = createJob({
        originZone: { id: 'z1', name: 'Naama Bay' },
      });
      expect(getOriginLabel(job)).toBe('Naama Bay');
    });

    it('returns em dash when no origin is set', () => {
      const job = createJob({});
      expect(getOriginLabel(job)).toBe('\u2014');
    });

    it('prioritizes airport over hotel and zone', () => {
      const job = createJob({
        originAirport: { id: 'a1', name: 'Sharm Airport', code: 'SSH' },
        originHotel: { id: 'h1', name: 'Some Hotel' },
        originZone: { id: 'z1', name: 'Some Zone' },
      });
      expect(getOriginLabel(job)).toBe('Sharm Airport (SSH)');
    });

    it('prioritizes hotel over zone when no airport', () => {
      const job = createJob({
        originHotel: { id: 'h1', name: 'Hilton Sharm' },
        originZone: { id: 'z1', name: 'Naama Bay' },
      });
      expect(getOriginLabel(job)).toBe('Hilton Sharm');
    });
  });

  describe('getDestinationLabel', () => {
    it('returns airport name with code when destinationAirport is set', () => {
      const job = createJob({
        destinationAirport: { id: 'a2', name: 'Hurghada International', code: 'HRG' },
      });
      expect(getDestinationLabel(job)).toBe('Hurghada International (HRG)');
    });

    it('returns hotel name when destinationHotel is set (no airport)', () => {
      const job = createJob({
        destinationHotel: { id: 'h2', name: 'Steigenberger Al Dau' },
      });
      expect(getDestinationLabel(job)).toBe('Steigenberger Al Dau');
    });

    it('returns zone name when destinationZone is set (no airport or hotel)', () => {
      const job = createJob({
        destinationZone: { id: 'z2', name: 'El Gouna' },
      });
      expect(getDestinationLabel(job)).toBe('El Gouna');
    });

    it('returns em dash when no destination is set', () => {
      const job = createJob({});
      expect(getDestinationLabel(job)).toBe('\u2014');
    });

    it('prioritizes airport over hotel and zone', () => {
      const job = createJob({
        destinationAirport: { id: 'a2', name: 'Luxor Airport', code: 'LXR' },
        destinationHotel: { id: 'h2', name: 'Some Hotel' },
        destinationZone: { id: 'z2', name: 'Some Zone' },
      });
      expect(getDestinationLabel(job)).toBe('Luxor Airport (LXR)');
    });
  });

  describe('getRouteLabel', () => {
    it('returns "Origin -> Destination" format', () => {
      const job = createJob({
        originAirport: { id: 'a1', name: 'Cairo International', code: 'CAI' },
        destinationHotel: { id: 'h2', name: 'Marriott Mena House' },
      });
      expect(getRouteLabel(job)).toBe('Cairo International (CAI) \u2192 Marriott Mena House');
    });

    it('shows em dashes for both when no locations set', () => {
      const job = createJob({});
      expect(getRouteLabel(job)).toBe('\u2014 \u2192 \u2014');
    });

    it('handles airport-to-airport routes', () => {
      const job = createJob({
        originAirport: { id: 'a1', name: 'Cairo', code: 'CAI' },
        destinationAirport: { id: 'a2', name: 'Sharm', code: 'SSH' },
      });
      expect(getRouteLabel(job)).toBe('Cairo (CAI) \u2192 Sharm (SSH)');
    });

    it('handles hotel-to-hotel routes', () => {
      const job = createJob({
        originHotel: { id: 'h1', name: 'Hotel A' },
        destinationHotel: { id: 'h2', name: 'Hotel B' },
      });
      expect(getRouteLabel(job)).toBe('Hotel A \u2192 Hotel B');
    });

    it('handles zone-to-zone routes', () => {
      const job = createJob({
        originZone: { id: 'z1', name: 'Zone A' },
        destinationZone: { id: 'z2', name: 'Zone B' },
      });
      expect(getRouteLabel(job)).toBe('Zone A \u2192 Zone B');
    });
  });
});
