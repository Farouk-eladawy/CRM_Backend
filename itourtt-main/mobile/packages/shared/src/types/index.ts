// ─── Enums ──────────────────────────────────────────────────────
export type UserRole = 'ADMIN' | 'DISPATCHER' | 'ACCOUNTANT' | 'AGENT_MANAGER' | 'VIEWER' | 'REP' | 'DRIVER' | 'SUPPLIER';
// TWO_WAY_TRANSFER / CITY_TO_CITY are legacy: not selectable, still present on old rows.
export type ServiceType = 'ARR' | 'DEP' | 'DAY_TOUR' | 'ONE_WAY_TRANSFER' | 'RETURN' | 'TWO_WAY_TRANSFER' | 'CITY_TO_CITY';
export type JobStatus = 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
export type PortalJobStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
export type VehicleOwnership = 'OWNED' | 'RENTED' | 'CONTRACTED';
export type Currency = 'EGP' | 'USD' | 'EUR' | 'GBP' | 'SAR';
export type InvoiceStatus = 'DRAFT' | 'POSTED' | 'PAID' | 'CANCELLED';
export type PaymentMethod = 'CASH' | 'BANK_TRANSFER' | 'CHECK';
export type B2CPaymentMethod = 'ONLINE' | 'PAY_ON_ARRIVAL';
export type B2CPaymentGateway = 'STRIPE' | 'EGYPT_BANK' | 'DUBAI_BANK';
export type B2CPaymentStatus = 'PENDING' | 'PAID' | 'REFUNDED' | 'FAILED';
export type GuestBookingStatus = 'CONFIRMED' | 'CANCELLED' | 'CONVERTED';
export type NotificationType = 'JOB_ASSIGNED' | 'JOB_UPDATED' | 'GENERAL';

// ─── Auth ───────────────────────────────────────────────────────
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  roleId?: string;
  roleSlug?: string;
  repId?: string;
  driverId?: string;
  supplierId?: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
}

export interface LoginPayload {
  identifier: string;
  password: string;
}

// ─── Locations ──────────────────────────────────────────────────
export interface Country {
  id: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
}

export interface Airport {
  id: string;
  name: string;
  code: string;
  countryId: string;
  country?: Country;
  createdAt: string;
  updatedAt: string;
}

export interface City {
  id: string;
  name: string;
  airportId: string;
  airport?: Airport;
  createdAt: string;
  updatedAt: string;
}

export interface Zone {
  id: string;
  name: string;
  cityId: string;
  city?: City;
  createdAt: string;
  updatedAt: string;
}

export interface Hotel {
  id: string;
  name: string;
  zoneId: string;
  zone?: Zone;
  createdAt: string;
  updatedAt: string;
}

export interface LocationTree {
  countries: (Country & {
    airports: (Airport & {
      cities: (City & {
        zones: (Zone & {
          hotels: Hotel[];
        })[];
      })[];
    })[];
  })[];
}

// ─── Vehicles ───────────────────────────────────────────────────
export interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
  createdAt: string;
  updatedAt: string;
}

export interface Vehicle {
  id: string;
  plateNumber: string;
  vehicleTypeId: string;
  vehicleType?: VehicleType;
  ownership: VehicleOwnership;
  color?: string | null;
  carBrand?: string | null;
  carModel?: string | null;
  makeYear?: number | null;
  luggageCapacity?: number | null;
  supplierId?: string | null;
  supplier?: { id: string; legalName: string; tradeName?: string | null } | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// ─── Drivers ────────────────────────────────────────────────────
export interface Driver {
  id: string;
  name: string;
  mobileNumber: string;
  licenseNumber: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface DriverVehicle {
  id: string;
  driverId: string;
  vehicleId: string;
  driver?: Driver;
  vehicle?: Vehicle;
  isPrimary: boolean;
  assignedAt: string;
  unassignedAt: string | null;
}

// ─── Reps ───────────────────────────────────────────────────────
export interface Rep {
  id: string;
  name: string;
  mobileNumber: string;
  feePerFlight?: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// ─── Agents ─────────────────────────────────────────────────────
export interface Agent {
  id: string;
  legalName: string;
  tradeName: string;
  taxId: string;
  phone: string;
  email: string;
  currency: Currency;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// ─── Customers ──────────────────────────────────────────────────
export interface Customer {
  id: string;
  legalName: string;
  tradeName: string | null;
  currency: Currency;
  creditLimit: number | null;
  creditDays: number | null;
  createdAt: string;
  updatedAt: string;
}

// ─── Suppliers ──────────────────────────────────────────────────
export interface Supplier {
  id: string;
  legalName: string;
  tradeName: string;
  phone: string;
  email: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// ─── Traffic Jobs ───────────────────────────────────────────────
export interface TrafficFlight {
  id: string;
  trafficJobId: string;
  flightNo: string;
  carrier: string;
  terminal: string | null;
  arrivalTime: string | null;
  departureTime: string | null;
}

export interface TrafficAssignment {
  id: string;
  trafficJobId: string;
  vehicleId: string;
  driverId: string | null;
  repId: string | null;
  vehicle?: Vehicle;
  driver?: Driver;
  rep?: Rep;
  assignedById: string;
  assignedAt: string;
}

export interface TrafficJob {
  id: string;
  internalRef: string;
  agentRef: string | null;
  agentId: string | null;
  customerId: string | null;
  agent?: Agent;
  customer?: Customer;
  serviceType: ServiceType;
  jobDate: string;
  status: JobStatus;
  paxCount: number;
  adultCount?: number;
  childCount?: number;
  originAirportId: string | null;
  originZoneId: string | null;
  originHotelId: string | null;
  destinationAirportId: string | null;
  destinationZoneId: string | null;
  destinationHotelId: string | null;
  originAirport?: Airport;
  originZone?: Zone;
  originHotel?: Hotel;
  destinationAirport?: Airport;
  destinationZone?: Zone;
  destinationHotel?: Hotel;
  notes: string | null;
  flight?: TrafficFlight;
  assignment?: TrafficAssignment;
  clientName?: string | null;
  clientMobile?: string | null;
  pickUpTime?: string | null;
  boosterSeat?: boolean;
  boosterSeatQty?: number;
  babySeat?: boolean;
  babySeatQty?: number;
  wheelChair?: boolean;
  wheelChairQty?: number;
  printSign?: boolean;
  collectionRequired?: boolean;
  collectionAmount?: number | null;
  collectionCurrency?: Currency;
  collectionCollected?: boolean;
  collectionLiquidated?: boolean;
  custRepName?: string | null;
  custRepMobile?: string | null;
  custRepMeetingPoint?: string | null;
  custRepMeetingTime?: string | null;
  createdAt: string;
  updatedAt: string;
}

// ─── Portal Job Types ───────────────────────────────────────────
export interface PortalJob {
  id: string;
  internalRef: string;
  serviceType: ServiceType;
  jobDate: string;
  status: JobStatus;
  paxCount: number;
  adultCount?: number;
  childCount?: number;
  clientName: string | null;
  clientMobile: string | null;
  pickUpTime: string | null;
  notes: string | null;
  originAirport?: { id: string; name: string; code: string } | null;
  originZone?: { id: string; name: string } | null;
  originHotel?: { id: string; name: string } | null;
  destinationAirport?: { id: string; name: string; code: string } | null;
  destinationZone?: { id: string; name: string } | null;
  destinationHotel?: { id: string; name: string } | null;
  flight?: TrafficFlight;
  assignment?: TrafficAssignment;
  boosterSeat?: boolean;
  boosterSeatQty?: number;
  babySeat?: boolean;
  babySeatQty?: number;
  wheelChair?: boolean;
  wheelChairQty?: number;
  printSign?: boolean;
}

export interface DriverPortalJob extends PortalJob {
  driverStatus: PortalJobStatus;
  collectionRequired: boolean;
  collectionAmount: number | null;
  collectionCurrency: Currency | null;
  collectionCollected: boolean;
  feeEarned?: number;
}

export interface RepPortalJob extends PortalJob {
  repStatus: PortalJobStatus;
  feeEarned?: number;
  custRepName?: string | null;
  custRepMobile?: string | null;
  custRepMeetingPoint?: string | null;
  custRepMeetingTime?: string | null;
}

export interface SupplierPortalJob extends PortalJob {
  supplierStatus: PortalJobStatus;
  supplierNotes?: string | null;
}

// ─── Notifications ──────────────────────────────────────────────
export interface PortalNotification {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  isRead: boolean;
  createdAt: string;
}

// ─── Guest Booking ──────────────────────────────────────────────
export interface BookingExtras {
  boosterSeatQty: number;
  babySeatQty: number;
  wheelChairQty: number;
}

export interface QuoteRequest {
  serviceType: ServiceType;
  originAirportId?: string;
  originZoneId?: string;
  originHotelId?: string;
  destinationAirportId?: string;
  destinationZoneId?: string;
  destinationHotelId?: string;
  vehicleTypeId: string;
  paxCount: number;
}

export interface QuoteResponse {
  price: number;
  currency: Currency;
  breakdown?: Record<string, unknown>;
}

export interface CreateGuestBooking {
  serviceType: ServiceType;
  originAirportId?: string;
  originZoneId?: string;
  originHotelId?: string;
  destinationAirportId?: string;
  destinationZoneId?: string;
  destinationHotelId?: string;
  vehicleTypeId: string;
  jobDate: string;
  pickupTime?: string;
  paxCount: number;
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  guestCountry?: string;
  flightNo?: string;
  carrier?: string;
  terminal?: string;
  extras?: BookingExtras;
  notes?: string;
  paymentMethod: B2CPaymentMethod;
  paymentGateway?: B2CPaymentGateway;
}

export interface GuestBooking {
  id: string;
  bookingRef: string;
  status: GuestBookingStatus;
  serviceType: ServiceType;
  jobDate: string;
  pickupTime: string | null;
  paxCount: number;
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  price: number;
  currency: Currency;
  paymentStatus: B2CPaymentStatus;
  paymentMethod: B2CPaymentMethod;
  originAirport?: Airport;
  originZone?: Zone;
  originHotel?: Hotel;
  destinationAirport?: Airport;
  destinationZone?: Zone;
  destinationHotel?: Hotel;
  vehicleType?: VehicleType;
  createdAt: string;
}

// ─── API Response ───────────────────────────────────────────────
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// ─── Driver Profile ─────────────────────────────────────────────
export interface DriverProfile {
  id: string;
  name: string;
  mobileNumber: string;
  licenseNumber: string;
  vehicles: (DriverVehicle & { vehicle: Vehicle })[];
}

// ─── Rep Profile ────────────────────────────────────────────────
export interface RepProfile {
  id: string;
  name: string;
  mobileNumber: string;
  feePerFlight: number;
  zones: { id: string; zone: Zone }[];
}

// ─── Supplier Profile ───────────────────────────────────────────
export interface SupplierProfile {
  id: string;
  legalName: string;
  tradeName: string;
  phone: string;
  email: string;
  vehicles: Vehicle[];
  drivers: Driver[];
}
