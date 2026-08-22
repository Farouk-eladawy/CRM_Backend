import api from '../client';
import type {
  LocationTree,
  VehicleType,
  QuoteRequest,
  QuoteResponse,
  CreateGuestBooking,
  GuestBooking,
} from '../../types';

export const publicApi = {
  getLocations() {
    return api.get<LocationTree>('/public/locations');
  },

  getVehicleTypes() {
    return api.get<VehicleType[]>('/public/vehicle-types');
  },

  getQuote(params: QuoteRequest) {
    return api.post<QuoteResponse>('/public/quote', params);
  },

  createBooking(data: CreateGuestBooking) {
    return api.post<GuestBooking>('/public/bookings', data);
  },

  // Lookup/cancel require the email used to create the booking (ownership check).
  getBooking(ref: string, email: string) {
    return api.post<GuestBooking>(`/public/bookings/${ref}/lookup`, { email });
  },

  cancelBooking(ref: string, email: string) {
    return api.post(`/public/bookings/${ref}/cancel`, { email });
  },
};
