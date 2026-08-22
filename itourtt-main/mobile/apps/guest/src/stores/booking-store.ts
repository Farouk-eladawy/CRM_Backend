import { create } from 'zustand';
import type {
  ServiceType,
  B2CPaymentMethod,
  B2CPaymentGateway,
  BookingExtras,
} from '@itour/shared';

interface BookingState {
  // Step 1 - Search
  serviceType: ServiceType | '';
  fromZoneId: string;
  toZoneId: string;
  hotelId: string;
  originAirportId: string;
  destinationAirportId: string;
  jobDate: string;
  pickupTime: string;
  paxCount: number;

  // Step 2 - Vehicle select
  vehicleTypeId: string;
  quotePrice: number | null;
  quoteCurrency: string;
  quoteBreakdown: Record<string, unknown> | null;
  extras: BookingExtras;

  // Step 3 - Guest Details
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  guestCountry: string;
  flightNo: string;
  carrier: string;
  terminal: string;
  notes: string;

  // Step 4 - Payment
  paymentMethod: B2CPaymentMethod | '';
  paymentGateway: B2CPaymentGateway | '';

  // Result
  bookingRef: string;

  // Actions
  setField: <K extends keyof BookingState>(field: K, value: BookingState[K]) => void;
  setExtra: (key: keyof BookingExtras, value: number) => void;
  setQuote: (price: number, currency: string, breakdown: Record<string, unknown> | null) => void;
  reset: () => void;
}

const initialState = {
  serviceType: '' as ServiceType | '',
  fromZoneId: '',
  toZoneId: '',
  hotelId: '',
  originAirportId: '',
  destinationAirportId: '',
  jobDate: '',
  pickupTime: '',
  paxCount: 1,
  vehicleTypeId: '',
  quotePrice: null as number | null,
  quoteCurrency: 'USD',
  quoteBreakdown: null as Record<string, unknown> | null,
  extras: { boosterSeatQty: 0, babySeatQty: 0, wheelChairQty: 0 },
  guestName: '',
  guestEmail: '',
  guestPhone: '',
  guestCountry: '',
  flightNo: '',
  carrier: '',
  terminal: '',
  notes: '',
  paymentMethod: '' as B2CPaymentMethod | '',
  paymentGateway: '' as B2CPaymentGateway | '',
  bookingRef: '',
};

export const useBookingStore = create<BookingState>((set) => ({
  ...initialState,

  setField: (field, value) =>
    set({ [field]: value } as Partial<BookingState>),

  setExtra: (key, value) =>
    set((state) => ({
      extras: { ...state.extras, [key]: value },
    })),

  setQuote: (price, currency, breakdown) =>
    set({ quotePrice: price, quoteCurrency: currency, quoteBreakdown: breakdown }),

  reset: () => set({ ...initialState, extras: { boosterSeatQty: 0, babySeatQty: 0, wheelChairQty: 0 } }),
}));
