// ─── Enums ──────────────────────────────────────────────────────
export type UserRole = 'ADMIN' | 'DISPATCHER' | 'ACCOUNTANT' | 'AGENT_MANAGER' | 'VIEWER' | 'REP' | 'DRIVER' | 'SUPPLIER';
// TWO_WAY_TRANSFER / CITY_TO_CITY are legacy: not selectable, still present on old rows.
export type ServiceType = 'ARR' | 'DEP' | 'DAY_TOUR' | 'ONE_WAY_TRANSFER' | 'RETURN' | 'TWO_WAY_TRANSFER' | 'CITY_TO_CITY';
export type JobStatus = 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
export type VehicleOwnership = 'OWNED' | 'RENTED' | 'CONTRACTED';
export type Currency = 'EGP' | 'USD' | 'EUR' | 'GBP' | 'SAR';
export type InvoiceStatus = 'DRAFT' | 'POSTED' | 'PAID' | 'CANCELLED';
export type PaymentMethod = 'CASH' | 'BANK_TRANSFER' | 'CHECK';
export type DocumentType = 'TAX_CARD' | 'COMMERCIAL_REGISTER' | 'ID_COPY' | 'CONTRACT' | 'OTHER';
export type InvoiceCycleType = 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY';

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
  userId?: string | null;
  user?: { id: string; email: string; name: string; role: string; isActive: boolean } | null;
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
  address: string;
  city: string;
  country: string;
  phone: string;
  email: string;
  currency: Currency;
  isActive: boolean;
  creditTerms?: AgentCreditTerms;
  invoiceCycle?: AgentInvoiceCycle;
  documents?: AgentDocument[];
  createdAt: string;
  updatedAt: string;
}

export interface AgentCreditTerms {
  id: string;
  agentId: string;
  creditLimit: number;
  creditDays: number;
}

export interface AgentInvoiceCycle {
  id: string;
  agentId: string;
  cycleType: InvoiceCycleType;
  dayOfWeek: number | null;
  dayOfMonth: number | null;
}

export interface AgentDocument {
  id: string;
  agentId: string;
  documentType: DocumentType;
  fileUrl: string;
  fileName: string;
  expiresAt: string | null;
  createdAt: string;
}

// ─── Suppliers ──────────────────────────────────────────────────
export interface Supplier {
  id: string;
  legalName: string;
  tradeName: string;
  taxId: string;
  address: string;
  city: string;
  country: string;
  phone: string;
  email: string;
  userId?: string | null;
  user?: { id: string; email: string; name: string; role: string; isActive: boolean } | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SupplierTripPrice {
  id: string;
  supplierId: string;
  serviceType: ServiceType;
  fromZoneId: string;
  toZoneId: string;
  vehicleTypeId: string;
  price: number;
  driverTip: number;
  currency: Currency;
  effectiveFrom: string | null;
  effectiveTo: string | null;
  fromZone?: Zone;
  toZone?: Zone;
  vehicleType?: VehicleType;
}

export interface SupplierWithVehicles extends Supplier {
  vehicles?: Vehicle[];
}

// ─── Traffic Jobs ───────────────────────────────────────────────
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
  fromZoneId: string;
  toZoneId: string;
  hotelId: string | null;
  originAirportId: string | null;
  originZoneId: string | null;
  originHotelId: string | null;
  destinationAirportId: string | null;
  destinationZoneId: string | null;
  destinationHotelId: string | null;
  fromZone?: Zone;
  toZone?: Zone;
  hotel?: Hotel;
  originAirport?: Airport;
  originZone?: Zone;
  originHotel?: Hotel;
  destinationAirport?: Airport;
  destinationZone?: Zone;
  destinationHotel?: Hotel;
  notes: string | null;
  flight?: TrafficFlight;
  assignment?: TrafficAssignment;
  createdById: string;
  createdAt: string;
  updatedAt: string;
}

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

// ─── Finance ────────────────────────────────────────────────────
export interface AgentInvoice {
  id: string;
  agentId: string | null;
  customerId: string | null;
  agent?: Agent;
  customer?: Customer;
  invoiceNumber: string;
  invoiceDate: string;
  dueDate: string;
  currency: Currency;
  subtotal: number;
  taxAmount: number;
  total: number;
  exchangeRate: number;
  status: InvoiceStatus;
  postedAt: string | null;
  lines?: InvoiceLine[];
  payments?: Payment[];
  createdAt: string;
  updatedAt: string;
}

export interface InvoiceLine {
  id: string;
  invoiceId: string;
  trafficJobId: string;
  description: string;
  quantity: number;
  unitPrice: number;
  taxRate: number;
  taxAmount: number;
  lineTotal: number;
}

export interface Payment {
  id: string;
  agentInvoiceId: string;
  amount: number;
  currency: Currency;
  exchangeRate: number;
  paymentMethod: PaymentMethod;
  paymentDate: string;
  reference: string | null;
  isPosted: boolean;
}

// ─── Pagination ─────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// ─── Dispatch ───────────────────────────────────────────────────
export interface DispatchDayView {
  date: string;
  arrivals: TrafficJob[];
  departures: TrafficJob[];
  cityJobs: TrafficJob[];
}
