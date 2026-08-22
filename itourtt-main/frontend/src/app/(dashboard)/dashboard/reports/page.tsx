"use client";

import React, { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import {
  CalendarDays,
  Car,
  Building2,
  DollarSign,
  Eye,
  Loader2,
  RefreshCw,
  Search,
  UserCheck,
  FileSpreadsheet,
  Printer,
  ShieldCheck,
  AlertTriangle,
  ClipboardList,
  Camera,
  Truck,
  Plane,
  ChevronDown,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import JobDetailModal from "@/components/job-detail-modal";
import { SearchableCombobox } from "@/components/searchable-combobox";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Checkbox } from "@/components/ui/checkbox";
import api from "@/lib/api";
import { useT, useLocaleId } from "@/lib/i18n";
import { formatDate , localDateStr } from "@/lib/utils";
import { SortableHeader } from "@/components/sortable-header";
import { useSortable } from "@/hooks/use-sortable";
import { useAuthStore } from "@/stores/auth-store";
import { useCompanyStore } from "@/stores/company-store";
import { usePermission } from "@/hooks/use-permission";
import { StatusBadge } from "@/components/ui/status-badge";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { DraggableTableHeader, type ColumnDef } from "@/components/ui/draggable-table-header";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { SERVICE_TYPE_DROPDOWN_OPTIONS, useServiceTypeLabel } from "@/lib/service-types";

// ────────────────────────────────────────────
// Types
// ────────────────────────────────────────────

interface DispatchSummary {
  date: string;
  totalJobs: number;
  assignedCount: number;
  unassignedCount: number;
  completionRate: number;
  assignmentRate: number;
  byStatus: Record<string, number>;
  byServiceType: Record<string, number>;
  jobs: Array<{
    id: string;
    internalRef: string;
    serviceType: string;
    status: string;
    paxCount: number;
    agent: { legalName: string } | null;
    customer: { legalName: string } | null;
    assignment: {
      vehicle: { plateNumber: string; vehicleType: { name: string } } | null;
      driver: { name: string } | null;
      rep: { name: string } | null;
    } | null;
  }>;
}

interface DriverJobScore {
  attendance: boolean;
  appearance: boolean;
  carCleanliness: boolean;
  maintenance: boolean;
  work: boolean;
  total: number;
  evaluation: string;
}

interface DriverTripReport {
  from: string;
  to: string;
  totalDrivers: number;
  totalTrips: number;
  drivers: Array<{
    driver: { id: string; name: string; mobileNumber: string };
    tripCount: number;
    totalFees: number;
    scoredCount: number;
    missingScores: number;
    avgScore: number | null;
    trips: Array<{
      jobId: string;
      internalRef: string;
      jobDate: string;
      serviceType: string;
      status: string;
      paxCount: number;
      route: string;
      agent: string;
      tripFee: number | null;
      tariffFee: number | null;
      driverJobScore: DriverJobScore | null;
    }>;
  }>;
}

interface AgentStatement {
  agent: {
    id: string;
    legalName: string;
    tradeName: string | null;
    currency: string;
    creditLimit: number | null;
    creditDays: number | null;
  };
  period: { from: string; to: string };
  jobCount: number;
  totalInvoiced: number;
  totalPaid: number;
  outstandingBalance: number;
  invoices: Array<{
    invoiceNumber: string;
    invoiceDate: string;
    dueDate: string;
    currency: string;
    total: number;
    paid: number;
    balance: number;
    status: string;
    lineCount: number;
  }>;
}

interface RevenueReport {
  period: { from: string; to: string };
  totalRevenue: number;
  totalCosts: number;
  grossProfit: number;
  profitMargin: number;
  costBreakdown: {
    driverFees: number;
    repFees: number;
    supplierCosts: number;
  };
  byServiceType: Record<string, number>;
  byAgent: Array<{
    agentId: string;
    name: string;
    revenue: number;
    invoiceCount: number;
    jobCount: number;
  }>;
}

interface RepJobScore {
  attendance: boolean;
  appearance: boolean;
  work: boolean;
  survey: boolean;
  review: boolean;
  total: number | null;
  fee: number | null;
  evaluation: string | null;
}

interface RepFeeReport {
  date: string;
  grandTotal: number;
  totalFlights: number;
  reps: Array<{
    repId: string;
    repName: string;
    feePerFlight: number;
    flightCount: number;
    totalAmount: number;
    fees: Array<{
      id: string;
      amount: number;
      status: string;
      isPosted: boolean;
      repStatus: string | null;
      inPlaceEvidence: Array<{ imageUrls: string[]; gpsMapLink: string | null; createdAt: string }>;
      hasSurvey: boolean;
      repJobScore: RepJobScore | null;
      trafficJob: {
        id: string;
        internalRef: string;
        serviceType: string;
        paxCount: number;
        status: string;
        fromZone: { name: string } | null;
        toZone: { name: string } | null;
        originAirport?: { name: string; code: string } | null;
        originZone?: { name: string } | null;
        originHotel?: { name: string } | null;
        destinationAirport?: { name: string; code: string } | null;
        destinationZone?: { name: string } | null;
        destinationHotel?: { name: string } | null;
        hotel: { name: string } | null;
        pickUpTime: string | null;
        flight: {
          flightNo: string;
          carrier: string;
          terminal: string | null;
          arrivalTime: string | null;
        } | null;
      };
    }>;
  }>;
}

interface RepFeeReportRep {
  repId: string;
  repName: string;
  feePerFlight: number;
  flightCount: number;
  totalAmount: number;
  fees: RepFeeReport["reps"][number]["fees"];
}

interface RepScoreRow {
  jobId: string;
  internalRef: string;
  serviceType: string;
  paxCount: number;
  status: string;
  repId: string;
  repName: string;
  fromZone: { name: string } | null;
  toZone: { name: string } | null;
  originAirport: { name: string; code: string } | null;
  originZone: { name: string } | null;
  originHotel: { name: string } | null;
  destinationAirport: { name: string; code: string } | null;
  destinationZone: { name: string } | null;
  destinationHotel: { name: string } | null;
  flightNo: string | null;
  carrier: string | null;
  attendance: boolean;
  appearance: boolean;
  work: boolean;
  review: boolean;
  total: number;
  fee: number;
  evaluation: string;
}

interface RepScoreReport {
  from: string;
  to: string;
  rows: RepScoreRow[];
  totalScore: number;
  avgScore: number;
  count: number;
  totalFee: number;
}

interface GuestSurveyRow {
  id: string;
  jobId: string;
  internalRef: string;
  jobDate: string;
  submittedAt: string;
  repId: string;
  repName: string;
  ageRange: string;
  noOfAdults: number;
  noOfChildren: number;
  noOfInfants: number;
  flightNo: string;
  stayLength: string | null;
  jobReference: string;
  repeaterGuest: string;
  guestNationality: string;
  localTravelAgent: string | null;
  hotelName: string;
  email: string | null;
  generalComment: string;
  contactNumber: string;
}

interface GuestSurveyReport {
  from: string;
  to: string;
  count: number;
  reps: Array<{ repId: string; repName: string; count: number }>;
  rows: GuestSurveyRow[];
}

interface DriverScoreRow {
  jobId: string;
  internalRef: string;
  jobDate: string;
  serviceType: string;
  paxCount: number;
  status: string;
  driverId: string;
  driverName: string;
  route: string;
  attendance: boolean;
  appearance: boolean;
  carCleanliness: boolean;
  maintenance: boolean;
  work: boolean;
  total: number;
  multiplier: number;
  feePercent: number;
  evaluation: string;
}

interface DriverScoreReport {
  from: string;
  to: string;
  rows: DriverScoreRow[];
  totalScore: number;
  avgScore: number;
  count: number;
}

interface ComplianceReportItem {
  vehicleId: string;
  plateNumber: string;
  vehicleTypeName: string;
  ownership: string;
  licenseExpiryDate: string | null;
  hasInsurance: boolean;
  insuranceExpiryDate: string | null;
  annualPayment: number | null;
  annualPaymentCurrency: string | null;
  gpsSubscription: number | null;
  tourismSupportFund: number | null;
  registrationFees: number | null;
  temporaryPermitDate: string | null;
  temporaryPermitExpiryDate: string | null;
  totalFees: number | null;
  depositTotal: number | null;
  balanceRemaining: number | null;
}

interface JobStatusReport {
  from: string;
  to: string;
  totalJobs: number;
  jobs: Array<{
    id: string;
    internalRef: string;
    agentRef: string | null;
    agentName: string | null;
    serviceDate: string;
    serviceType: string;
    time: string | null;
    priceAmount: number | null;
    priceCurrency: string | null;
    transferPrice: number | null;
    transferPriceCurrency: string | null;
    status: string;
    repJobStatus: string | null;
    driverJobStatus: string | null;
    repName: string | null;
    driverName: string | null;
    flightNo: string | null;
    driverEvidence: EvidenceItem[];
  }>;
}

interface EvidenceItem {
  id: string;
  imageUrls: string[];
  gpsMapLink: string;
  submittedBy: string;
  createdAt: string;
}

interface EvidenceReportRow {
  jobId: string;
  internalRef: string;
  agentName: string | null;
  agentRef: string | null;
  jobDate: string;
  serviceType: string;
  status: string;
  paxCount: number;
  clientName: string | null;
  fromZone: { name: string } | null;
  toZone: { name: string } | null;
  originAirport: { name: string; code: string } | null;
  destinationAirport: { name: string; code: string } | null;
  originHotel: { name: string } | null;
  destinationHotel: { name: string } | null;
  pickUpTime: string | null;
  flight: {
    flightNo: string;
    carrier: string;
    terminal: string | null;
    arrivalTime: string | null;
    departureTime: string | null;
  } | null;
  driverName: string | null;
  repName: string | null;
  assignment: {
    vehicle: { plateNumber: string } | null;
    driver: { name: string } | null;
    rep: { name: string } | null;
  } | null;
  noShowEvidence: EvidenceItem[];
  inPlaceEvidence: EvidenceItem[];
  completedEvidence: EvidenceItem[];
  hasEvidence: boolean;
}

interface EvidenceReport {
  from: string;
  to: string;
  totalJobs: number;
  rows: EvidenceReportRow[];
}

interface Agent {
  id: string;
  legalName: string;
}

interface CarJobRow {
  id: string;
  jobRef: string;
  agentName: string;
  serviceDate: string;
  origin: string;
  destination: string;
  driver: string;
  jobStatus: string;
  plateNumber: string;
  transferPrice: number | null;
  transferPriceCurrency: string;
}

interface CarJobsReport {
  total: number;
  rows: CarJobRow[];
  totals: { USD: number; EUR: number; EGP: number };
}

interface SupplierJobRow {
  id: string;
  jobRef: string;
  agentName: string;
  agentRef: string;
  serviceDate: string;
  route: string;
  supplierName: string;
  supplierStatus: string;
}

interface SupplierJobsReport {
  total: number;
  rows: SupplierJobRow[];
}

interface VisaReportRow {
  clientName: string;
  flightNo: string;
  arrivalTime: string | null;
  terminal: string;
}

interface VisaReport {
  from: string;
  to: string;
  count: number;
  rows: VisaReportRow[];
}

interface SalesReportRow {
  internalRef: string;
  agentRef: string;
  flightNo: string;
  terminal: string;
  arrivalTime: string | null;
  pax: number;
  hotelName: string;
  clientName: string;
  clientNumber: string;
}

interface SalesReport {
  from: string;
  to: string;
  count: number;
  rows: SalesReportRow[];
}

interface DepartureReportRow {
  serviceDate: string;
  customerName: string;
  customerNumber: string;
  pax: number;
  pickupTime: string | null;
  serviceType: string;
}

interface DepartureReport {
  from: string;
  to: string;
  count: number;
  rows: DepartureReportRow[];
}

interface FlightDelayRow {
  internalRef: string;
  agentRef: string | null;
  jobDate: string | null;
  oldArrivalDate: string | null;
  oldArrivalTime: string | null;
  newArrivalDate: string;
  newArrivalTime: string;
  reportedBy: string;
  currentRepName: string | null;
  reportedAt: string;
}

interface FlightDelayReport {
  from: string;
  to: string;
  count: number;
  rows: FlightDelayRow[];
}

interface ReviewReportRow {
  internalRef: string;
  agentName: string;
  agentRef: string;
  serviceDate: string;
  serviceType: string;
  status: string;
  pax: number;
  clientName: string;
  origin: string;
  destination: string;
  transferPrice: number | null;
  transferPriceCurrency: string;
  driverName: string;
  repName: string;
  notes: string;
}

interface ReviewReport {
  from: string;
  to: string;
  count: number;
  rows: ReviewReportRow[];
}

// ────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────

const today = localDateStr(new Date());
const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000)
  .toISOString()
  .split("T")[0];

const fmt = (n: number, locale = "en-US") =>
  n.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });


// ────────────────────────────────────────────
// Column definitions for draggable headers
// ────────────────────────────────────────────

const DISPATCH_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Ref" },
  { key: "serviceType", label: "Type" },
  { key: "agent", label: "Agent" },
  { key: "paxCount", label: "Pax" },
  { key: "vehicle", label: "Vehicle" },
  { key: "driver", label: "Driver" },
  { key: "status", label: "Status" },
];
const DISPATCH_DEFAULT_KEYS = DISPATCH_COLUMNS.map((c) => c.key);

const DRIVERS_COLUMNS: ColumnDef[] = [
  { key: "driverName", label: "Driver" },
  { key: "mobile", label: "Mobile" },
  { key: "trips", label: "Trips", className: "text-right" },
  { key: "avgScore", label: "Avg Score", className: "text-right" },
  { key: "missing", label: "Missing", className: "text-right" },
  { key: "totalFees", label: "Total Fees", className: "text-right" },
];
const DRIVERS_DEFAULT_KEYS = DRIVERS_COLUMNS.map((c) => c.key);

const DRIVER_SCORE_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Job Ref" },
  { key: "jobDate", label: "Date" },
  { key: "serviceType", label: "Type" },
  { key: "paxCount", label: "Pax", className: "text-right" },
  { key: "driverName", label: "Driver" },
  { key: "route", label: "Route" },
  { key: "status", label: "Status" },
  { key: "attendance", label: <>Att<br /><span className="text-muted-foreground">30pt</span></>, className: "text-center" },
  { key: "appearance", label: <>App<br /><span className="text-muted-foreground">20pt</span></>, className: "text-center" },
  { key: "carCleanliness", label: <>Car<br /><span className="text-muted-foreground">10pt</span></>, className: "text-center" },
  { key: "maintenance", label: <>Maint<br /><span className="text-muted-foreground">10pt</span></>, className: "text-center" },
  { key: "work", label: <>Work<br /><span className="text-muted-foreground">30pt</span></>, className: "text-center" },
  { key: "total", label: "Score", className: "text-right" },
  { key: "feePercent", label: "Fee %", className: "text-right" },
  { key: "evaluation", label: "Evaluation" },
];
const DRIVER_SCORE_DEFAULT_KEYS = DRIVER_SCORE_COLUMNS.map((c) => c.key);

const AGENT_COLUMNS: ColumnDef[] = [
  { key: "invoiceNumber", label: "Invoice No" },
  { key: "invoiceDate", label: "Date" },
  { key: "dueDate", label: "Due Date" },
  { key: "total", label: "Total", className: "text-right" },
  { key: "paid", label: "Paid", className: "text-right" },
  { key: "balance", label: "Balance", className: "text-right" },
  { key: "status", label: "Status" },
];
const AGENT_DEFAULT_KEYS = AGENT_COLUMNS.map((c) => c.key);

const REP_FEES_COLUMNS: ColumnDef[] = [
  { key: "repName", label: "Rep Name" },
  { key: "feePerFlight", label: "Fee/Flight", className: "text-right" },
  { key: "flightCount", label: "Flights", className: "text-right" },
  { key: "totalAmount", label: "Total", className: "text-right" },
];
const REP_FEES_DEFAULT_KEYS = REP_FEES_COLUMNS.map((c) => c.key);

const REP_SCORE_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Job Ref" },
  { key: "flightNo", label: "Flight No" },
  { key: "serviceType", label: "Type" },
  { key: "paxCount", label: "Pax", className: "text-right" },
  { key: "repName", label: "Rep" },
  { key: "route", label: "Route" },
  { key: "hotel", label: "Hotel" },
  { key: "status", label: "Status" },
  { key: "attendance", label: <>Att<br /><span className="text-muted-foreground">20pt</span></>, className: "text-center" },
  { key: "appearance", label: <>App<br /><span className="text-muted-foreground">15pt</span></>, className: "text-center" },
  { key: "work", label: <>Work<br /><span className="text-muted-foreground">30pt</span></>, className: "text-center" },
  { key: "review", label: <>Rev<br /><span className="text-muted-foreground">35pt</span></>, className: "text-center" },
  { key: "total", label: "Score", className: "text-right" },
  { key: "fee", label: "Fee", className: "text-right" },
  { key: "evaluation", label: "Evaluation" },
];
const REP_SCORE_DEFAULT_KEYS = REP_SCORE_COLUMNS.map((c) => c.key);

const REVENUE_COLUMNS: ColumnDef[] = [
  { key: "agentName", label: "Agent" },
  { key: "revenue", label: "Revenue", className: "text-right" },
  { key: "invoiceCount", label: "Invoices", className: "text-right" },
  { key: "jobCount", label: "Jobs", className: "text-right" },
];
const REVENUE_DEFAULT_KEYS = REVENUE_COLUMNS.map((c) => c.key);

const COMPLIANCE_COLUMNS: ColumnDef[] = [
  { key: "plateNumber", label: "Plate Number" },
  { key: "vehicleTypeName", label: "Type" },
  { key: "ownership", label: "Ownership" },
  { key: "licenseExpiryDate", label: "License Expiry" },
  { key: "insurance", label: "Insurance" },
  { key: "temporaryPermitDate", label: "Permit Date" },
  { key: "permitExpiry", label: "Permit Expiry" },
  { key: "annualPayment", label: "Annual Payment" },
  { key: "registrationFees", label: "Reg. Fees" },
  { key: "totalFees", label: "Total Fees" },
  { key: "depositTotal", label: "Deposits" },
  { key: "balanceRemaining", label: "Balance" },
];
const COMPLIANCE_DEFAULT_KEYS = COMPLIANCE_COLUMNS.map((c) => c.key);

const JOB_STATUS_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "TRSF Ref" },
  { key: "agentRef", label: "Agent Ref" },
  { key: "agentName", label: "Agent Name" },
  { key: "serviceDate", label: "Service Date" },
  { key: "serviceType", label: "Type" },
  { key: "time", label: "Time" },
  { key: "driverName", label: "Driver" },
  { key: "repName", label: "Rep" },
  { key: "priceAmount", label: "Price", className: "text-right" },
  { key: "status", label: "Status" },
  { key: "repJobStatus", label: "Rep Status" },
  { key: "driverJobStatus", label: "Driver Status" },
  { key: "flightNo", label: "Flight No" },
  { key: "evidence", label: "Evidence" },
];
const JOB_STATUS_DEFAULT_KEYS = JOB_STATUS_COLUMNS.map((c) => c.key);

const EVIDENCE_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Job Ref" },
  { key: "agentName", label: "Agent Name" },
  { key: "agentRef", label: "Agent Ref" },
  { key: "jobDate", label: "Date" },
  { key: "serviceType", label: "Type" },
  { key: "arrivalFlightTime", label: "Arr. Flight Time" },
  { key: "departurePickupTime", label: "Dep. Pickup Time" },
  { key: "status", label: "Status" },
  { key: "repName", label: "Rep" },
  { key: "driverName", label: "Driver" },
  { key: "evidence", label: "Evidence" },
];
const EVIDENCE_DEFAULT_KEYS = EVIDENCE_COLUMNS.map((c) => c.key);

const SUPPLIER_JOBS_COLUMNS: ColumnDef[] = [
  { key: "jobRef", label: "Job Ref" },
  { key: "agentName", label: "Agent Name" },
  { key: "agentRef", label: "Agent Ref" },
  { key: "serviceDate", label: "Service Date" },
  { key: "route", label: "Route" },
  { key: "supplierName", label: "Supplier" },
  { key: "supplierStatus", label: "Supplier Status" },
];
const SUPPLIER_JOBS_DEFAULT_KEYS = SUPPLIER_JOBS_COLUMNS.map((c) => c.key);

const CAR_JOBS_COLUMNS: ColumnDef[] = [
  { key: "jobRef", label: "Job Ref" },
  { key: "agentName", label: "Agent Name" },
  { key: "serviceDate", label: "Service Date" },
  { key: "origin", label: "Origin" },
  { key: "destination", label: "Destination" },
  { key: "plateNumber", label: "Vehicle" },
  { key: "driver", label: "Driver" },
  { key: "jobStatus", label: "Job Status" },
  { key: "usdPrice", label: "USD Transfer Price" },
  { key: "eurPrice", label: "EUR Transfer Price" },
  { key: "egpPrice", label: "EGP Transfer Price" },
];
const CAR_JOBS_DEFAULT_KEYS = CAR_JOBS_COLUMNS.map((c) => c.key);

const VISA_COLUMNS: ColumnDef[] = [
  { key: "clientName", label: "Client Name" },
  { key: "flightNo", label: "Flight Number" },
  { key: "arrivalTime", label: "Arrival Time" },
  { key: "terminal", label: "Terminal" },
];
const VISA_DEFAULT_KEYS = VISA_COLUMNS.map((c) => c.key);

const SALES_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Internal Ref" },
  { key: "agentRef", label: "Agent Ref" },
  { key: "flightNo", label: "Flight No." },
  { key: "terminal", label: "Terminal" },
  { key: "arrivalTime", label: "Arrival Time" },
  { key: "pax", label: "Pax", className: "text-right" },
  { key: "hotelName", label: "Hotel Name" },
  { key: "clientName", label: "Client Name" },
  { key: "clientNumber", label: "Client Number" },
];
const SALES_DEFAULT_KEYS = SALES_COLUMNS.map((c) => c.key);

const DEPARTURE_COLUMNS: ColumnDef[] = [
  { key: "serviceDate", label: "Service Date" },
  { key: "customerName", label: "Customer Name" },
  { key: "customerNumber", label: "Customer Number" },
  { key: "pax", label: "Pax", className: "text-right" },
  { key: "pickupTime", label: "Pickup Time" },
  { key: "serviceType", label: "Service Type" },
];
const DEPARTURE_DEFAULT_KEYS = DEPARTURE_COLUMNS.map((c) => c.key);

const FLIGHT_DELAY_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Internal Ref" },
  { key: "agentRef", label: "Agent Ref" },
  { key: "jobDate", label: "Service Date" },
  { key: "oldArrivalDate", label: "Old Arr. Date" },
  { key: "oldArrivalTime", label: "Old Arr. Time" },
  { key: "newArrivalDate", label: "New Arr. Date" },
  { key: "newArrivalTime", label: "New Arr. Time" },
  { key: "reportedBy", label: "Rep Name" },
  { key: "currentRepName", label: "Current Rep" },
];
const FLIGHT_DELAY_DEFAULT_KEYS = FLIGHT_DELAY_COLUMNS.map((c) => c.key);

const REVIEW_COLUMNS: ColumnDef[] = [
  { key: "internalRef", label: "Internal Ref" },
  { key: "agentName", label: "Agent Name" },
  { key: "agentRef", label: "Agent Ref" },
  { key: "serviceDate", label: "Service Date" },
  { key: "serviceType", label: "Service Type" },
  { key: "status", label: "Status" },
  { key: "pax", label: "Pax", className: "text-right" },
  { key: "clientName", label: "Client" },
  { key: "origin", label: "Origin" },
  { key: "destination", label: "Destination" },
  { key: "transferPrice", label: "Tr. Price", className: "text-right" },
  { key: "transferPriceCurrency", label: "Tr. Cur" },
  { key: "driverName", label: "Driver Name" },
  { key: "repName", label: "Rep Name" },
  { key: "notes", label: "Notes" },
];
const REVIEW_DEFAULT_KEYS = REVIEW_COLUMNS.map((c) => c.key);

// ────────────────────────────────────────────
// Stat Card
// ────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  color = "text-foreground",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <Card className="border-border bg-card px-2 py-px">
      <p className="text-[10px] text-muted-foreground leading-none truncate">{label}</p>
      <p className={`text-xs font-semibold leading-snug ${color}`}>{value}</p>
      {sub && <p className="text-[9px] text-muted-foreground leading-none">{sub}</p>}
    </Card>
  );
}

// ────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────

export default function ReportsPage() {
  const t = useT();
  const serviceTypeLabel = useServiceTypeLabel();
  const locale = useLocaleId();
  const { user } = useAuthStore();
  const { logoUrl, companyName } = useCompanyStore();

  const canDailyDispatch = usePermission("reports.dailyDispatch");
  const canDriverTrips = usePermission("reports.driverTrips");
  const canDriverScore = usePermission("reports.driverScore");
  const canAgentStatement = usePermission("reports.agentStatement");
  const canRepFees = usePermission("reports.repFees");
  const canRepScore = usePermission("reports.repScore");
  const canGuestSurveys = usePermission("reports.guestSurveys");
  const canRevenue = usePermission("reports.revenue");
  const canVehicleCompliance = usePermission("reports.vehicleCompliance");
  const canJobStatus = usePermission("reports.jobStatus");
  const canEvidence = usePermission("reports.evidence");
  const canSupplierJobs = usePermission("reports.supplierJobs");
  const canCarJobs = usePermission("reports.carJobs");
  const canVisa = usePermission("reports.visa");
  const canSales = usePermission("reports.sales");
  const canDeparture = usePermission("reports.departure");
  const canFlightDelay = usePermission("reports.flightDelay");
  const canReview = usePermission("reports.review");

  // Daily Dispatch
  const [dispatchDate, setDispatchDate] = useState(today);
  const [dispatchData, setDispatchData] = useState<DispatchSummary | null>(null);
  const [dispatchLoading, setDispatchLoading] = useState(false);

  // Driver Trips
  const [driverFrom, setDriverFrom] = useState(thirtyDaysAgo);
  const [driverTo, setDriverTo] = useState(today);
  const [driverData, setDriverData] = useState<DriverTripReport | null>(null);
  const [driverLoading, setDriverLoading] = useState(false);
  const [recalcLoading, setRecalcLoading] = useState(false);
  const [selectedDriver, setSelectedDriver] = useState<DriverTripReport["drivers"][number] | null>(null);
  const [driverMissedJobs, setDriverMissedJobs] = useState<Record<string, boolean>>({});
  const [driverDeductions, setDriverDeductions] = useState<Record<string, number>>({});
  const [driverModalOpen, setDriverModalOpen] = useState(false);
  const [driverScoreEdits, setDriverScoreEdits] = useState<Record<string, DriverJobScore>>({});
  const [driverScoreSaving, setDriverScoreSaving] = useState<Record<string, boolean>>({});

  // Agent Statement
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [agentFrom, setAgentFrom] = useState(thirtyDaysAgo);
  const [agentTo, setAgentTo] = useState(today);
  const [agentData, setAgentData] = useState<AgentStatement | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);

  // Revenue
  const [revenueFrom, setRevenueFrom] = useState(thirtyDaysAgo);
  const [revenueTo, setRevenueTo] = useState(today);
  const [revenueData, setRevenueData] = useState<RevenueReport | null>(null);
  const [revenueLoading, setRevenueLoading] = useState(false);

  // Rep Fees
  const [repFeeFrom, setRepFeeFrom] = useState(today);
  const [repFeeTo, setRepFeeTo] = useState(today);
  const [repFeeData, setRepFeeData] = useState<RepFeeReport | null>(null);
  const [repFeeLoading, setRepFeeLoading] = useState(false);
  const [selectedRep, setSelectedRep] = useState<RepFeeReportRep | null>(null);
  const [repModalOpen, setRepModalOpen] = useState(false);
  // scoreEdits: jobId → { attendance, appearance, work, review }
  const [scoreEdits, setScoreEdits] = useState<Record<string, RepJobScore>>({});
  const [scoreSaving, setScoreSaving] = useState<Record<string, boolean>>({});
  // missedJobs: jobId → true when rep missed the job (disables score checkboxes)
  const [missedJobs, setMissedJobs] = useState<Record<string, boolean>>({});
  // deductions: jobId → amount deducted from rep for missing a job
  const [deductions, setDeductions] = useState<Record<string, number>>({});
  // repNetTotals: repId → final computed net total (overrides server totalAmount in the list)
  const [repNetTotals, setRepNetTotals] = useState<Record<string, number>>({});
  const [evidenceViewOpen, setEvidenceViewOpen] = useState(false);
  const [evidenceViewJobRef, setEvidenceViewJobRef] = useState<string>("");
  const [evidenceViewUrls, setEvidenceViewUrls] = useState<string[]>([]);
  const [evidenceViewLoading, setEvidenceViewLoading] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);
  const dispatchPrintRef = useRef<HTMLDivElement>(null);
  const driverPrintRef = useRef<HTMLDivElement>(null);
  const agentPrintRef = useRef<HTMLDivElement>(null);
  const revenuePrintRef = useRef<HTMLDivElement>(null);
  const compliancePrintRef = useRef<HTMLDivElement>(null);

  // Vehicle Compliance
  const [complianceData, setComplianceData] = useState<ComplianceReportItem[]>([]);
  const [complianceLoading, setComplianceLoading] = useState(false);
  const [complianceOwnershipFilter, setComplianceOwnershipFilter] = useState("ALL");
  const [complianceTypeFilter, setComplianceTypeFilter] = useState("ALL");

  // Job Status
  const [jobStatusFrom, setJobStatusFrom] = useState(thirtyDaysAgo);
  const [jobStatusTo, setJobStatusTo] = useState(today);
  const [jobStatusFilter, setJobStatusFilter] = useState<string[]>([]);
  const [jobStatusRepId, setJobStatusRepId] = useState("ALL");
  const [jobStatusRepStatus, setJobStatusRepStatus] = useState("ALL");
  const [jobStatusDriverStatus, setJobStatusDriverStatus] = useState("ALL");
  const [jobStatusServiceType, setJobStatusServiceType] = useState("ALL");
  const [jobStatusData, setJobStatusData] = useState<JobStatusReport | null>(null);
  const [jobStatusLoading, setJobStatusLoading] = useState(false);
  const jobStatusPrintRef = useRef<HTMLDivElement>(null);
  const [jobDetailId, setJobDetailId] = useState<string | null>(null);
  const [evidencePdfLoading, setEvidencePdfLoading] = useState<Set<string>>(new Set());

  // Rep Score
  const [repScoreFrom, setRepScoreFrom] = useState(thirtyDaysAgo);
  const [repScoreTo, setRepScoreTo] = useState(today);
  const [repScoreRepId, setRepScoreRepId] = useState("ALL");
  const [repList, setRepList] = useState<Array<{ id: string; name: string }>>([]);
  const [repScoreData, setRepScoreData] = useState<RepScoreReport | null>(null);
  const [repScoreLoading, setRepScoreLoading] = useState(false);
  const repScorePrintRef = useRef<HTMLDivElement>(null);

  // Guest Surveys
  const [guestSurveyFrom, setGuestSurveyFrom] = useState(thirtyDaysAgo);
  const [guestSurveyTo, setGuestSurveyTo] = useState(today);
  const [guestSurveyRepId, setGuestSurveyRepId] = useState("ALL");
  const [guestSurveyData, setGuestSurveyData] = useState<GuestSurveyReport | null>(null);
  const [guestSurveyLoading, setGuestSurveyLoading] = useState(false);
  const guestSurveyPrintRef = useRef<HTMLDivElement>(null);

  // Driver Score
  const [driverScoreFrom, setDriverScoreFrom] = useState(thirtyDaysAgo);
  const [driverScoreTo, setDriverScoreTo] = useState(today);
  const [driverScoreDriverId, setDriverScoreDriverId] = useState("ALL");
  const [driverScoreData, setDriverScoreData] = useState<DriverScoreReport | null>(null);
  const [driverScoreLoading, setDriverScoreLoading] = useState(false);
  const driverScorePrintRef = useRef<HTMLDivElement>(null);

  // Car Jobs Report
  const [carJobsFrom, setCarJobsFrom] = useState(thirtyDaysAgo);
  const [carJobsTo, setCarJobsTo] = useState(today);
  const [carJobsVehicleId, setCarJobsVehicleId] = useState("ALL");
  const [carJobsData, setCarJobsData] = useState<CarJobsReport | null>(null);
  const [carJobsLoading, setCarJobsLoading] = useState(false);
  const [ownedVehicleList, setOwnedVehicleList] = useState<Array<{ id: string; plateNumber: string }>>([]);
  const carJobsPrintRef = useRef<HTMLDivElement>(null);

  // Supplier Jobs Report
  const [supplierJobsFrom, setSupplierJobsFrom] = useState(thirtyDaysAgo);
  const [supplierJobsTo, setSupplierJobsTo] = useState(today);
  const [supplierJobsSupplierId, setSupplierJobsSupplierId] = useState("ALL");
  const [supplierJobsStatus, setSupplierJobsStatus] = useState("ALL");
  const [supplierJobsData, setSupplierJobsData] = useState<SupplierJobsReport | null>(null);
  const [supplierJobsLoading, setSupplierJobsLoading] = useState(false);
  const [supplierList, setSupplierList] = useState<Array<{ id: string; name: string }>>([]);
  const supplierJobsPrintRef = useRef<HTMLDivElement>(null);

  // Evidence Report
  const [evidenceFrom, setEvidenceFrom] = useState(thirtyDaysAgo);
  const [evidenceTo, setEvidenceTo] = useState(today);
  const [evidenceStatusFilter, setEvidenceStatusFilter] = useState("ALL");
  const [evidenceAgentId, setEvidenceAgentId] = useState("ALL");
  const [evidenceRepId, setEvidenceRepId] = useState("ALL");
  const [evidenceDriverId, setEvidenceDriverId] = useState("ALL");
  const [driverList, setDriverList] = useState<Array<{ id: string; name: string }>>([]);
  const [evidenceData, setEvidenceData] = useState<EvidenceReport | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);

  // Visa Report
  const [visaFrom, setVisaFrom] = useState(thirtyDaysAgo);
  const [visaTo, setVisaTo] = useState(today);
  const [visaData, setVisaData] = useState<VisaReport | null>(null);
  const [visaLoading, setVisaLoading] = useState(false);
  const visaPrintRef = useRef<HTMLDivElement>(null);

  // Sales Report
  const [salesFrom, setSalesFrom] = useState(thirtyDaysAgo);
  const [salesTo, setSalesTo] = useState(today);
  const [salesData, setSalesData] = useState<SalesReport | null>(null);
  const [salesLoading, setSalesLoading] = useState(false);
  const salesPrintRef = useRef<HTMLDivElement>(null);

  // Departure Report
  const [departureFrom, setDepartureFrom] = useState(thirtyDaysAgo);
  const [departureTo, setDepartureTo] = useState(today);
  const [departureServiceType, setDepartureServiceType] = useState("DEP");
  const [departureData, setDepartureData] = useState<DepartureReport | null>(null);
  const [departureLoading, setDepartureLoading] = useState(false);
  const departurePrintRef = useRef<HTMLDivElement>(null);

  // Flight Delay Report
  const [flightDelayFrom, setFlightDelayFrom] = useState(thirtyDaysAgo);
  const [flightDelayTo, setFlightDelayTo] = useState(today);
  const [flightDelayRepName, setFlightDelayRepName] = useState("ALL");
  const [flightDelayData, setFlightDelayData] = useState<FlightDelayReport | null>(null);
  const [flightDelayLoading, setFlightDelayLoading] = useState(false);
  const flightDelayPrintRef = useRef<HTMLDivElement>(null);

  // Review Report
  const [reviewFrom, setReviewFrom] = useState(thirtyDaysAgo);
  const [reviewTo, setReviewTo] = useState(today);
  const [reviewStatus, setReviewStatus] = useState<string[]>([]);
  const [reviewData, setReviewData] = useState<ReviewReport | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const reviewPrintRef = useRef<HTMLDivElement>(null);

  // Derived: filtered compliance data and unique vehicle types
  const complianceVehicleTypes = Array.from(new Set(complianceData.map((v) => v.vehicleTypeName).filter(Boolean))).sort();
  const filteredComplianceData = complianceData.filter((v) => {
    if (complianceOwnershipFilter !== "ALL" && v.ownership !== complianceOwnershipFilter) return false;
    if (complianceTypeFilter !== "ALL" && v.vehicleTypeName !== complianceTypeFilter) return false;
    return true;
  });

  // Sortable hooks for each report table
  const dispatchSort = useSortable(dispatchData?.jobs || []);
  const driverSort = useSortable(driverData?.drivers || []);
  const agentSort = useSortable(agentData?.invoices || []);
  const repFeeSort = useSortable(repFeeData?.reps || []);
  const revenueSort = useSortable(revenueData?.byAgent || []);
  const complianceSort = useSortable(filteredComplianceData);
  const jobStatusSort = useSortable(jobStatusData?.jobs || []);
  const supplierJobsSort = useSortable(supplierJobsData?.rows || []);
  const carJobsSort = useSortable(carJobsData?.rows || []);
  const visaSort = useSortable(visaData?.rows || []);
  const salesSort = useSortable(salesData?.rows || []);
  const departureSort = useSortable(departureData?.rows || []);
  const flightDelaySort = useSortable(flightDelayData?.rows || []);
  const reviewSort = useSortable(reviewData?.rows || []);

  // Column order hooks for drag-and-drop reordering
  const dispatchColOrder = useColumnPreferences("dispatch", DISPATCH_DEFAULT_KEYS);
  const driversColOrder = useColumnPreferences("drivers", DRIVERS_DEFAULT_KEYS);
  const driverScoreColOrder = useColumnPreferences("driver_score", DRIVER_SCORE_DEFAULT_KEYS);
  const agentColOrder = useColumnPreferences("agent_statement", AGENT_DEFAULT_KEYS);
  const repFeesColOrder = useColumnPreferences("rep_fees", REP_FEES_DEFAULT_KEYS);
  const repScoreColOrder = useColumnPreferences("rep_score", REP_SCORE_DEFAULT_KEYS);
  const revenueColOrder = useColumnPreferences("revenue", REVENUE_DEFAULT_KEYS);
  const complianceColOrder = useColumnPreferences("compliance", COMPLIANCE_DEFAULT_KEYS);
  const jobStatusColOrder = useColumnPreferences("job_status", JOB_STATUS_DEFAULT_KEYS);
  const evidenceColOrder = useColumnPreferences("evidence", EVIDENCE_DEFAULT_KEYS);
  const supplierJobsColOrder = useColumnPreferences("supplier_jobs", SUPPLIER_JOBS_DEFAULT_KEYS);
  const carJobsColOrder = useColumnPreferences("car_jobs", CAR_JOBS_DEFAULT_KEYS);
  const visaColOrder = useColumnPreferences("visa", VISA_DEFAULT_KEYS);
  const salesColOrder = useColumnPreferences("sales", SALES_DEFAULT_KEYS);
  const departureColOrder = useColumnPreferences("departure", DEPARTURE_DEFAULT_KEYS);
  const flightDelayColOrder = useColumnPreferences("flight_delay", FLIGHT_DELAY_DEFAULT_KEYS);
  const reviewColOrder = useColumnPreferences("review", REVIEW_DEFAULT_KEYS);

  // Load agents list for agent statement
  useEffect(() => {
    api
      .get("/agents")
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.data || [];
        setAgents(list);
      })
      .catch(() => {});
  }, []);

  // Load reps list for rep score filter
  useEffect(() => {
    api
      .get("/reps", { params: { isActive: true, limit: 1000 } })
      .then(({ data }) => {
        const list: Array<{ id: string; name: string }> = Array.isArray(data) ? data : data.data || [];
        setRepList(list.map((r) => ({ id: r.id, name: r.name })));
      })
      .catch(() => {});
  }, []);

  // Load owned active vehicles for car jobs filter
  useEffect(() => {
    if (!canCarJobs) return;
    api
      .get("/export/odoo/car-jobs/vehicles")
      .then(({ data }) => {
        const list: Array<{ id: string; plateNumber: string }> =
          Array.isArray(data) ? data : data.data || [];
        setOwnedVehicleList(list);
      })
      .catch(() => {});
  }, [canCarJobs]);

  // Load suppliers list for supplier jobs filter
  useEffect(() => {
    if (!canSupplierJobs) return;
    api
      .get("/suppliers?limit=500")
      .then(({ data }) => {
        const list: Array<{ id: string; tradeName?: string; legalName?: string }> =
          Array.isArray(data) ? data : data.data || [];
        setSupplierList(
          list.map((s) => ({ id: s.id, name: s.tradeName ?? s.legalName ?? s.id }))
        );
      })
      .catch(() => {});
  }, [canSupplierJobs]);

  // Load drivers list for driver trips & evidence report filters
  useEffect(() => {
    if (!canDriverTrips && !canEvidence) return;
    api
      .get("/drivers?limit=500&isActive=true")
      .then(({ data }) => {
        const list: Array<{ id: string; name: string }> = Array.isArray(data) ? data : data.data || [];
        setDriverList(list.map((d) => ({ id: d.id, name: d.name })));
      })
      .catch(() => {});
  }, [canDriverTrips, canEvidence]);

  // ── Fetch functions ──

  const fetchDispatch = async () => {
    setDispatchLoading(true);
    try {
      const { data } = await api.get(
        `/reports/daily-dispatch?date=${dispatchDate}`
      );
      setDispatchData(data.data || data);
    } catch {
      toast.error(t("reports.failedDispatch"));
    } finally {
      setDispatchLoading(false);
    }
  };

  const fetchDriverTrips = async () => {
    setDriverLoading(true);
    try {
      const { data } = await api.get(
        `/reports/driver-trips?from=${driverFrom}&to=${driverTo}`
      );
      setDriverData(data.data || data);
    } catch {
      toast.error(t("reports.failedDriverTrips"));
    } finally {
      setDriverLoading(false);
    }
  };

  const recalculateDriverFees = async () => {
    setRecalcLoading(true);
    try {
      const { data } = await api.post(`/traffic-jobs/recalculate-driver-fees`, {
        from: driverFrom,
        to: driverTo,
      });
      const result = data.data || data;
      toast.success(`Fees recalculated: ${result.created} created, ${result.skipped} skipped`);
      await fetchDriverTrips();
    } catch {
      toast.error("Failed to recalculate driver fees");
    } finally {
      setRecalcLoading(false);
    }
  };

  const fetchAgentStatement = async () => {
    if (!selectedAgentId) {
      toast.error(t("reports.selectAgentRequired"));
      return;
    }
    setAgentLoading(true);
    try {
      const { data } = await api.get(
        `/reports/agent-statement/${selectedAgentId}?from=${agentFrom}&to=${agentTo}`
      );
      setAgentData(data.data || data);
    } catch {
      toast.error(t("reports.failedAgentStatement"));
    } finally {
      setAgentLoading(false);
    }
  };

  const fetchRevenue = async () => {
    setRevenueLoading(true);
    try {
      const { data } = await api.get(
        `/reports/revenue?from=${revenueFrom}&to=${revenueTo}`
      );
      setRevenueData(data.data || data);
    } catch {
      toast.error(t("reports.failedRevenue"));
    } finally {
      setRevenueLoading(false);
    }
  };

  const fetchRepFees = async () => {
    setRepFeeLoading(true);
    try {
      const { data } = await api.get(
        `/reports/rep-fees?from=${repFeeFrom}&to=${repFeeTo}`
      );
      setRepFeeData(data.data || data);
      // Reset per-rep overrides whenever a fresh report is loaded
      setMissedJobs({});
      setDeductions({});
      setRepNetTotals({});
    } catch {
      toast.error(t("reports.failedRepFees"));
    } finally {
      setRepFeeLoading(false);
    }
  };

  const saveRepScore = async (
    jobId: string,
    score: { attendance: boolean; appearance: boolean; work: boolean; survey: boolean; review: boolean },
  ) => {
    setScoreSaving((s) => ({ ...s, [jobId]: true }));
    try {
      await api.put(`/reports/rep-score/${jobId}`, score);
      // Recompute the score locally (weights must match rep-score.util.ts)
      const total =
        (score.attendance ? 20 : 0) +
        (score.appearance ? 15 : 0) +
        (score.work ? 15 : 0) +
        (score.survey ? 15 : 0) +
        (score.review ? 35 : 0);
      let fee = 20, evaluation = "Poor";
      if (total >= 90) { fee = 50; evaluation = "Excellent"; }
      else if (total >= 75) { fee = 40; evaluation = "Good"; }
      else if (total >= 61) { fee = 30; evaluation = "Average"; }
      const newScore: RepJobScore = { ...score, total, fee, evaluation };
      setScoreEdits((s) => ({ ...s, [jobId]: newScore }));
      // Patch repFeeData so the summary totals update
      setRepFeeData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          reps: prev.reps.map((r) => ({
            ...r,
            fees: r.fees.map((f) =>
              f.trafficJob.id === jobId
                ? { ...f, amount: f.trafficJob.serviceType === "ARR" ? fee : f.amount, repJobScore: newScore }
                : f,
            ),
            totalAmount: r.fees.reduce((sum, f) => {
              if (f.trafficJob.serviceType !== "ARR") return sum;
              const amt = f.trafficJob.id === jobId ? fee : Number(f.amount);
              return sum + amt;
            }, 0),
          })),
        };
      });
    } catch {
      toast.error("Failed to save score");
    } finally {
      setScoreSaving((s) => ({ ...s, [jobId]: false }));
    }
  };

  const saveDriverScore = async (
    jobId: string,
    score: { attendance: boolean; appearance: boolean; carCleanliness: boolean; maintenance: boolean; work: boolean },
  ) => {
    setDriverScoreSaving((s) => ({ ...s, [jobId]: true }));
    try {
      await api.put(`/reports/driver-score/${jobId}`, score);
      const total =
        (score.attendance ? 30 : 0) +
        (score.appearance ? 20 : 0) +
        (score.carCleanliness ? 10 : 0) +
        (score.maintenance ? 10 : 0) +
        (score.work ? 20 : 0);
      let evaluation = "Poor";
      if (total >= 81) evaluation = "Excellent";
      else if (total >= 63) evaluation = "Good";
      else if (total >= 45) evaluation = "Average";
      const newScore: DriverJobScore = { ...score, total, evaluation };
      setDriverScoreEdits((s) => ({ ...s, [jobId]: newScore }));
      // Patch driverData so the modal stays in sync
      setDriverData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          drivers: prev.drivers.map((d) => ({
            ...d,
            trips: d.trips.map((t) =>
              t.jobId === jobId ? { ...t, driverJobScore: newScore } : t,
            ),
          })),
        };
      });
    } catch {
      toast.error("Failed to save driver score");
    } finally {
      setDriverScoreSaving((s) => ({ ...s, [jobId]: false }));
    }
  };

  const fetchCompliance = async () => {
    setComplianceLoading(true);
    try {
      const { data } = await api.get("/vehicles/compliance/report");
      setComplianceData(data.data || []);
    } catch {
      toast.error(t("reports.failedCompliance"));
    } finally {
      setComplianceLoading(false);
    }
  };

  const fetchJobStatus = async () => {
    setJobStatusLoading(true);
    try {
      const statusParam = jobStatusFilter.length > 0 ? `&status=${jobStatusFilter.join(",")}` : "";
      const repParam = jobStatusRepId !== "ALL" ? `&repId=${jobStatusRepId}` : "";
      const repStatusParam = jobStatusRepStatus !== "ALL" ? `&repStatus=${jobStatusRepStatus}` : "";
      const driverStatusParam = jobStatusDriverStatus !== "ALL" ? `&driverStatus=${jobStatusDriverStatus}` : "";
      const serviceTypeParam = jobStatusServiceType !== "ALL" ? `&serviceType=${jobStatusServiceType}` : "";
      const { data } = await api.get(
        `/reports/job-status?from=${jobStatusFrom}&to=${jobStatusTo}${statusParam}${repParam}${repStatusParam}${driverStatusParam}${serviceTypeParam}`
      );
      setJobStatusData(data.data || data);
    } catch {
      toast.error(t("reports.failedJobStatus"));
    } finally {
      setJobStatusLoading(false);
    }
  };

  const exportJobStatusPdf = () => printFromRef(jobStatusPrintRef, `Job Status Report - ${jobStatusFrom} to ${jobStatusTo}`);

  const exportJobStatusExcel = async () => {
    try {
      const params = new URLSearchParams({ from: jobStatusFrom, to: jobStatusTo });
      if (jobStatusFilter.length > 0) params.set("status", jobStatusFilter.join(","));
      if (jobStatusRepId !== "ALL") params.set("repId", jobStatusRepId);
      if (jobStatusRepStatus !== "ALL") params.set("repStatus", jobStatusRepStatus);
      if (jobStatusDriverStatus !== "ALL") params.set("driverStatus", jobStatusDriverStatus);
      if (jobStatusServiceType !== "ALL") params.set("serviceType", jobStatusServiceType);
      const res = await api.get(`/export/odoo/job-status?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `job_status_${jobStatusFrom}_to_${jobStatusTo}.xlsx`);
    } catch {
      toast.error("Failed to export job status to Excel");
    }
  };

  const fetchCarJobs = async () => {
    setCarJobsLoading(true);
    try {
      const params = new URLSearchParams({ from: carJobsFrom, to: carJobsTo });
      if (carJobsVehicleId !== "ALL") params.set("vehicleId", carJobsVehicleId);
      const { data } = await api.get(`/export/odoo/car-jobs?${params.toString()}`);
      setCarJobsData(data.data ?? data);
    } catch {
      toast.error("Failed to load car jobs report");
    } finally {
      setCarJobsLoading(false);
    }
  };

  const exportCarJobsPdf = () =>
    printFromRef(carJobsPrintRef, `Car Jobs - ${carJobsFrom} to ${carJobsTo}`);

  const exportCarJobsExcel = async () => {
    try {
      const params = new URLSearchParams({ from: carJobsFrom, to: carJobsTo });
      if (carJobsVehicleId !== "ALL") params.set("vehicleId", carJobsVehicleId);
      const res = await api.get(`/export/odoo/car-jobs-excel?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `car_jobs_${carJobsFrom}_to_${carJobsTo}.xlsx`);
    } catch {
      toast.error("Failed to export car jobs to Excel");
    }
  };

  const fetchSupplierJobs = async () => {
    setSupplierJobsLoading(true);
    try {
      const params = new URLSearchParams({ from: supplierJobsFrom, to: supplierJobsTo });
      if (supplierJobsSupplierId !== "ALL") params.set("supplierId", supplierJobsSupplierId);
      if (supplierJobsStatus !== "ALL") params.set("supplierStatus", supplierJobsStatus);
      const { data } = await api.get(`/export/odoo/supplier-jobs?${params.toString()}`);
      setSupplierJobsData(data.data ?? data);
    } catch {
      toast.error("Failed to load supplier jobs report");
    } finally {
      setSupplierJobsLoading(false);
    }
  };

  const exportSupplierJobsPdf = () =>
    printFromRef(supplierJobsPrintRef, `Supplier Jobs - ${supplierJobsFrom} to ${supplierJobsTo}`);

  const exportSupplierJobsExcel = async () => {
    try {
      const params = new URLSearchParams({ from: supplierJobsFrom, to: supplierJobsTo });
      if (supplierJobsSupplierId !== "ALL") params.set("supplierId", supplierJobsSupplierId);
      if (supplierJobsStatus !== "ALL") params.set("supplierStatus", supplierJobsStatus);
      const res = await api.get(`/export/odoo/supplier-jobs-excel?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `supplier_jobs_${supplierJobsFrom}_to_${supplierJobsTo}.xlsx`);
    } catch {
      toast.error("Failed to export supplier jobs to Excel");
    }
  };

  const downloadEvidenceZip = async (jobId: string, ref: string) => {
    setEvidencePdfLoading((prev) => new Set(prev).add(jobId));
    try {
      const res = await api.get(`/export/odoo/evidence-zip/${jobId}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `evidence_${ref}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download evidence ZIP");
    } finally {
      setEvidencePdfLoading((prev) => { const s = new Set(prev); s.delete(jobId); return s; });
    }
  };

  const downloadDriverEvidencePdf = (job: JobStatusReport["jobs"][number]) =>
    downloadEvidenceZip(job.id, job.internalRef);

  const fetchEvidenceReport = async () => {
    setEvidenceLoading(true);
    try {
      const statusParam = evidenceStatusFilter !== "ALL" ? `&status=${evidenceStatusFilter}` : "";
      const agentParam = evidenceAgentId !== "ALL" ? `&agentId=${evidenceAgentId}` : "";
      const repParam = evidenceRepId !== "ALL" ? `&repId=${evidenceRepId}` : "";
      const driverParam = evidenceDriverId !== "ALL" ? `&driverId=${evidenceDriverId}` : "";
      const { data } = await api.get(
        `/reports/evidence?from=${evidenceFrom}&to=${evidenceTo}${statusParam}${agentParam}${repParam}${driverParam}`
      );
      setEvidenceData(data.data || data);
    } catch {
      toast.error("Failed to load evidence report");
    } finally {
      setEvidenceLoading(false);
    }
  };

  const generateEvidencePdf = (row: EvidenceReportRow) =>
    downloadEvidenceZip(row.jobId, row.internalRef);

  const exportEvidenceExcel = async () => {
    try {
      const params = new URLSearchParams({ from: evidenceFrom, to: evidenceTo });
      if (evidenceStatusFilter !== "ALL") params.set("status", evidenceStatusFilter);
      if (evidenceAgentId !== "ALL") params.set("agentId", evidenceAgentId);
      if (evidenceRepId !== "ALL") params.set("repId", evidenceRepId);
      if (evidenceDriverId !== "ALL") params.set("driverId", evidenceDriverId);
      const res = await api.get(`/export/odoo/evidence-excel?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `evidence_${evidenceFrom}_to_${evidenceTo}.xlsx`);
    } catch {
      toast.error("Failed to export evidence report to Excel");
    }
  };

  const isDriveId = (url: string) => /^[A-Za-z0-9_-]{20,}$/.test(url);

  const openEvidenceView = async (imageUrls: string[], jobRef: string) => {
    setEvidenceViewJobRef(jobRef);
    setEvidenceViewUrls([]);
    setEvidenceViewOpen(true);
    setEvidenceViewLoading(true);
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
    const resolved = await Promise.all(
      imageUrls.map(async (url) => {
        if (isDriveId(url)) {
          try {
            const res = await api.get(`/export/odoo/evidence-file/${url}`, { responseType: "blob" });
            return URL.createObjectURL(res.data);
          } catch {
            return null;
          }
        }
        // Local path like /uploads/no-show/filename.jpg
        return url.startsWith("http") ? url : `${apiBase}${url}`;
      })
    );
    const loaded = resolved.filter(Boolean) as string[];
    setEvidenceViewUrls(loaded);
    if (loaded.length === 0 && imageUrls.length > 0) {
      toast.error("Failed to load evidence images — Google Drive may not be configured");
    } else if (loaded.length < imageUrls.length) {
      toast.error("Some evidence images could not be loaded");
    }
    setEvidenceViewLoading(false);
  };

  const fetchRepScore = async () => {
    setRepScoreLoading(true);
    try {
      const repParam = repScoreRepId !== "ALL" ? `&repId=${repScoreRepId}` : "";
      const { data } = await api.get(
        `/reports/rep-score?from=${repScoreFrom}&to=${repScoreTo}${repParam}`
      );
      setRepScoreData(data.data || data);
    } catch {
      toast.error("Failed to load rep score report");
    } finally {
      setRepScoreLoading(false);
    }
  };

  const fetchGuestSurveys = async () => {
    setGuestSurveyLoading(true);
    try {
      const repParam = guestSurveyRepId !== "ALL" ? `&repId=${guestSurveyRepId}` : "";
      const { data } = await api.get(
        `/reports/guest-surveys?from=${guestSurveyFrom}&to=${guestSurveyTo}${repParam}`
      );
      setGuestSurveyData(data.data || data);
    } catch {
      toast.error("Failed to load guest survey report");
    } finally {
      setGuestSurveyLoading(false);
    }
  };

  const exportGuestSurveysPdf = () => printFromRef(guestSurveyPrintRef, `Guest Surveys - ${guestSurveyFrom} to ${guestSurveyTo}`);

  const exportGuestSurveysExcel = async () => {
    try {
      const repParam = guestSurveyRepId !== "ALL" ? `&repId=${guestSurveyRepId}` : "";
      const res = await api.get(`/export/odoo/guest-surveys?from=${guestSurveyFrom}&to=${guestSurveyTo}${repParam}`, { responseType: "blob" });
      downloadBlob(res.data, `guest_surveys_${guestSurveyFrom}_to_${guestSurveyTo}.xlsx`);
    } catch {
      toast.error("Failed to export guest surveys to Excel");
    }
  };

  const exportRepScorePdf = () => printFromRef(repScorePrintRef, `Rep Score Report - ${repScoreFrom} to ${repScoreTo}`);

  const exportRepScoreExcel = async () => {
    try {
      const repParam = repScoreRepId !== "ALL" ? `&repId=${repScoreRepId}` : "";
      const res = await api.get(`/export/odoo/rep-score?from=${repScoreFrom}&to=${repScoreTo}${repParam}`, { responseType: "blob" });
      downloadBlob(res.data, `rep_score_${repScoreFrom}_to_${repScoreTo}.xlsx`);
    } catch {
      toast.error("Failed to export rep score to Excel");
    }
  };

  const fetchDriverScore = async () => {
    setDriverScoreLoading(true);
    try {
      const driverParam = driverScoreDriverId !== "ALL" ? `&driverId=${driverScoreDriverId}` : "";
      const { data } = await api.get(
        `/reports/driver-score?from=${driverScoreFrom}&to=${driverScoreTo}${driverParam}`
      );
      setDriverScoreData(data.data || data);
    } catch {
      toast.error("Failed to load driver score report");
    } finally {
      setDriverScoreLoading(false);
    }
  };

  const exportDriverScorePdf = () => printFromRef(driverScorePrintRef, `Driver Score Report - ${driverScoreFrom} to ${driverScoreTo}`);

  const exportDriverScoreExcel = async () => {
    try {
      const driverParam = driverScoreDriverId !== "ALL" ? `&driverId=${driverScoreDriverId}` : "";
      const res = await api.get(`/export/odoo/driver-score?from=${driverScoreFrom}&to=${driverScoreTo}${driverParam}`, { responseType: "blob" });
      downloadBlob(res.data, `driver_score_${driverScoreFrom}_to_${driverScoreTo}.xlsx`);
    } catch {
      toast.error("Failed to export driver score to Excel");
    }
  };

  const exportRepFeesExcel = async () => {
    try {
      const res = await api.get(
        `/export/odoo/rep-fees?from=${repFeeFrom}&to=${repFeeTo}`,
        { responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `rep_fees_${repFeeFrom}_to_${repFeeTo}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("reports.failedExcel"));
    }
  };

  const exportRepFeesPdf = () => {
    if (!printRef.current) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      toast.error(t("reports.allowPopups"));
      return;
    }
    const now = new Date().toLocaleString();
    const userName = user?.name || "System";
    const logoHtml = logoUrl
      ? `<img src="${logoUrl}" alt="Logo" style="height:48px;max-width:160px;object-fit:contain;" />`
      : `<span style="font-size:18px;font-weight:700;">${companyName}</span>`;
    printWindow.document.write(`
      <html><head><title>Rep Fees Report - ${repFeeFrom} to ${repFeeTo}</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; color: #111; }
        h1 { font-size: 18px; margin-bottom: 4px; }
        h2 { font-size: 14px; color: #555; margin-bottom: 16px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 12px; }
        th { background: #f5f5f5; font-weight: 600; }
        .text-right { text-align: right; }
        .total-row { font-weight: 700; background: #f9f9f9; }
        .group-header { background: #eef; font-weight: 600; }
        .report-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 2px solid #111; }
        .report-header .logo { flex-shrink: 0; }
        .report-header .report-title { font-size: 20px; font-weight: 700; text-align: center; flex: 1; }
        .report-footer { display: flex; justify-content: space-between; margin-top: 32px; padding-top: 12px; border-top: 1px solid #ccc; font-size: 11px; color: #555; }
        @media print {
          body { padding: 0; }
          .report-footer { position: fixed; bottom: 20px; left: 20px; right: 20px; }
        }
      </style></head><body>
      <div class="report-header">
        <div class="logo">${logoHtml}</div>
        <div class="report-title">Rep Fees Report - ${repFeeFrom} to ${repFeeTo}</div>
        <div style="width:160px;"></div>
      </div>
      ${printRef.current.innerHTML}
      <div class="report-footer">
        <span>Issued By: ${userName}</span>
        <span>Issued on ${now}</span>
      </div>
      </body></html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); printWindow.close(); }, 300);
  };

  // ── Generic helpers ──

  const downloadBlob = (data: Blob, filename: string) => {
    const url = window.URL.createObjectURL(data);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const printFromRef = (ref: React.RefObject<HTMLDivElement | null>, title: string) => {
    if (!ref.current) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) { toast.error(t("reports.allowPopups")); return; }
    const now = new Date().toLocaleString();
    const userName = user?.name || "System";
    const logoHtml = logoUrl
      ? `<img src="${logoUrl}" alt="Logo" style="height:48px;max-width:160px;object-fit:contain;" />`
      : `<span style="font-size:18px;font-weight:700;">${companyName}</span>`;
    printWindow.document.write(`
      <html><head><title>${title}</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; color: #111; }
        h1 { font-size: 18px; margin-bottom: 4px; }
        h2 { font-size: 14px; color: #555; margin-bottom: 16px; }
        h3 { font-size: 13px; margin-top: 16px; margin-bottom: 8px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 12px; }
        th { background: #f5f5f5; font-weight: 600; }
        .text-right { text-align: right; }
        .total-row { font-weight: 700; background: #f9f9f9; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 20px; margin-bottom: 16px; font-size: 12px; }
        .info-grid dt { color: #666; } .info-grid dd { font-weight: 600; margin: 0; }
        .report-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 2px solid #111; }
        .report-header .logo { flex-shrink: 0; }
        .report-header .report-title { font-size: 20px; font-weight: 700; text-align: center; flex: 1; }
        .report-footer { display: flex; justify-content: space-between; margin-top: 32px; padding-top: 12px; border-top: 1px solid #ccc; font-size: 11px; color: #555; }
        @media print {
          body { padding: 0; }
          .report-footer { position: fixed; bottom: 20px; left: 20px; right: 20px; }
        }
      </style></head><body>
      <div class="report-header">
        <div class="logo">${logoHtml}</div>
        <div class="report-title">${title}</div>
        <div style="width:160px;"></div>
      </div>
      ${ref.current.innerHTML}
      <div class="report-footer">
        <span>Issued By: ${userName}</span>
        <span>Issued on ${now}</span>
      </div>
      </body></html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); printWindow.close(); }, 300);
  };

  // ── Daily Dispatch Export ──
  const exportDispatchExcel = async () => {
    try {
      const res = await api.get(`/export/odoo/daily-dispatch?date=${dispatchDate}`, { responseType: "blob" });
      downloadBlob(new Blob([res.data]), `daily_dispatch_${dispatchDate}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };
  const exportDispatchPdf = () => printFromRef(dispatchPrintRef, `Daily Dispatch - ${dispatchDate}`);

  // ── Driver Trips Export ──
  const exportDriverTripsExcel = async () => {
    try {
      const res = await api.get(`/export/odoo/driver-trips?from=${driverFrom}&to=${driverTo}`, { responseType: "blob" });
      downloadBlob(new Blob([res.data]), `driver_trips_${driverFrom}_${driverTo}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };
  const exportDriverTripsPdf = () => printFromRef(driverPrintRef, `Driver Trips - ${driverFrom} to ${driverTo}`);

  // ── Agent Statement Export ──
  const exportAgentStatementExcel = async () => {
    try {
      const res = await api.get(`/export/odoo/agent-statement/${selectedAgentId}?from=${agentFrom}&to=${agentTo}`, { responseType: "blob" });
      downloadBlob(new Blob([res.data]), `agent_statement_${agentFrom}_${agentTo}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };
  const exportAgentStatementPdf = () => printFromRef(agentPrintRef, `Agent Statement - ${agentData?.agent.legalName || ""}`);

  // ── Revenue Export ──
  const exportRevenueExcel = async () => {
    try {
      const res = await api.get(`/export/odoo/revenue?from=${revenueFrom}&to=${revenueTo}`, { responseType: "blob" });
      downloadBlob(new Blob([res.data]), `revenue_${revenueFrom}_${revenueTo}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };
  const exportRevenuePdf = () => printFromRef(revenuePrintRef, `Revenue Report - ${revenueFrom} to ${revenueTo}`);

  // ── Vehicle Compliance Export ──
  const exportComplianceExcel = async () => {
    try {
      const res = await api.get("/export/odoo/vehicle-compliance", { responseType: "blob" });
      downloadBlob(new Blob([res.data]), "vehicle_compliance.xlsx");
    } catch { toast.error(t("reports.failedExcel")); }
  };
  const exportCompliancePdf = () => printFromRef(compliancePrintRef, "Vehicle Compliance Report");

  // ── Visa Report ──
  const fetchVisa = async () => {
    setVisaLoading(true);
    try {
      const { data } = await api.get(`/reports/visa?from=${visaFrom}&to=${visaTo}`);
      setVisaData(data.data || data);
    } catch {
      toast.error("Failed to load visa report");
    } finally {
      setVisaLoading(false);
    }
  };

  const exportVisaExcel = async () => {
    try {
      const res = await api.get(`/export/odoo/visa?from=${visaFrom}&to=${visaTo}`, { responseType: "blob" });
      downloadBlob(new Blob([res.data]), `visa_${visaFrom}_${visaTo}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };

  const exportVisaPdf = () => printFromRef(visaPrintRef, `Visa Report - ${visaFrom} to ${visaTo}`);

  // ── Sales Report ──
  const fetchSales = async () => {
    setSalesLoading(true);
    try {
      const { data } = await api.get(`/reports/sales?from=${salesFrom}&to=${salesTo}`);
      setSalesData(data.data || data);
    } catch {
      toast.error("Failed to load sales report");
    } finally {
      setSalesLoading(false);
    }
  };

  const exportSalesExcel = async () => {
    try {
      const res = await api.get(`/export/odoo/sales?from=${salesFrom}&to=${salesTo}`, { responseType: "blob" });
      downloadBlob(new Blob([res.data]), `sales_${salesFrom}_${salesTo}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };

  const exportSalesPdf = () => printFromRef(salesPrintRef, `Sales Report - ${salesFrom} to ${salesTo}`);

  // ── Departure Report ──
  const fetchDeparture = async () => {
    setDepartureLoading(true);
    try {
      const stParam = departureServiceType !== "ALL" ? `&serviceType=${departureServiceType}` : "";
      const { data } = await api.get(`/reports/departure?from=${departureFrom}&to=${departureTo}${stParam}`);
      setDepartureData(data.data || data);
    } catch {
      toast.error("Failed to load departure report");
    } finally {
      setDepartureLoading(false);
    }
  };

  const exportDeparturePdf = () => printFromRef(departurePrintRef, `Departure Report - ${departureFrom} to ${departureTo}`);

  const exportDepartureExcel = async () => {
    try {
      const params = new URLSearchParams({ from: departureFrom, to: departureTo });
      if (departureServiceType !== "ALL") params.set("serviceType", departureServiceType);
      const res = await api.get(`/export/odoo/departure?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `departure_${departureFrom}_to_${departureTo}.xlsx`);
    } catch {
      toast.error("Failed to export departure report to Excel");
    }
  };

  // ── Flight Delay Report ──
  const fetchFlightDelay = async () => {
    setFlightDelayLoading(true);
    try {
      const repParam = flightDelayRepName !== "ALL" ? `&repName=${encodeURIComponent(flightDelayRepName)}` : "";
      const { data } = await api.get(`/reports/flight-delay?from=${flightDelayFrom}&to=${flightDelayTo}${repParam}`);
      setFlightDelayData(data.data || data);
    } catch {
      toast.error("Failed to load flight delay report");
    } finally {
      setFlightDelayLoading(false);
    }
  };

  const exportFlightDelayPdf = () => printFromRef(flightDelayPrintRef, `Flight Delay Report - ${flightDelayFrom} to ${flightDelayTo}`);

  const exportFlightDelayExcel = async () => {
    try {
      const params = new URLSearchParams({ from: flightDelayFrom, to: flightDelayTo });
      if (flightDelayRepName !== "ALL") params.set("repName", flightDelayRepName);
      const res = await api.get(`/export/odoo/flight-delay?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `flight_delay_${flightDelayFrom}_to_${flightDelayTo}.xlsx`);
    } catch {
      toast.error("Failed to export flight delay report to Excel");
    }
  };

  // ── Review Report ──
  const fetchReview = async () => {
    setReviewLoading(true);
    try {
      const params = new URLSearchParams({ from: reviewFrom, to: reviewTo });
      if (reviewStatus.length > 0) params.set("status", reviewStatus.join(","));
      const { data } = await api.get(`/reports/review?${params.toString()}`);
      setReviewData(data.data || data);
    } catch {
      toast.error("Failed to load review report");
    } finally {
      setReviewLoading(false);
    }
  };

  const exportReviewExcel = async () => {
    try {
      const params = new URLSearchParams({ from: reviewFrom, to: reviewTo });
      if (reviewStatus.length > 0) params.set("status", reviewStatus.join(","));
      const res = await api.get(`/export/odoo/review?${params.toString()}`, { responseType: "blob" });
      downloadBlob(res.data, `review_${reviewFrom}_${reviewTo}.xlsx`);
    } catch { toast.error(t("reports.failedExcel")); }
  };

  const exportReviewPdf = () => printFromRef(reviewPrintRef, `Review Report - ${reviewFrom} to ${reviewTo}`);

  // Compute final net total for a rep using current scoreEdits / missedJobs / deductions
  function computeRepNet(fees: RepFeeReportRep["fees"]): number {
    const gross = fees.reduce((sum, fee) => {
      const jobId = fee.trafficJob.id;
      if (missedJobs[jobId]) return sum;
      const score = scoreEdits[jobId] ?? fee.repJobScore;
      const feeAmt = fee.trafficJob.serviceType === "ARR"
        ? (score?.fee ?? fee.amount)
        : fee.amount;
      return sum + (Number(feeAmt) || 0);
    }, 0);
    const relevantJobIds = new Set(fees.map((f) => f.trafficJob.id));
    const totalDeductions = Object.entries(deductions)
      .filter(([k]) => relevantJobIds.has(k))
      .reduce((s, [, v]) => s + (Number(v) || 0), 0);
    return gross - totalDeductions;
  }

  // Group fees by flight number for the modal
  function groupByFlight(fees: RepFeeReportRep["fees"]) {
    const groups = new Map<
      string,
      { flightNo: string; carrier: string; jobs: typeof fees }
    >();
    for (const fee of fees) {
      const flightNo = fee.trafficJob.flight?.flightNo || "No Flight";
      const carrier = fee.trafficJob.flight?.carrier || "";
      const key = `${flightNo}|${carrier}`;
      const existing = groups.get(key);
      if (existing) {
        existing.jobs.push(fee);
      } else {
        groups.set(key, { flightNo, carrier, jobs: [fee] });
      }
    }
    return Array.from(groups.values());
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("reports.title")}
        description={t("reports.description")}
      />

      <Tabs defaultValue={
        canDailyDispatch ? "dispatch" :
        canDriverTrips ? "drivers" :
        canDriverScore ? "driver-score" :
        canAgentStatement ? "agent" :
        canRepFees ? "rep-fees" :
        canRepScore ? "rep-score" :
        canRevenue ? "revenue" :
        canVehicleCompliance ? "compliance" :
        canJobStatus ? "job-status" :
        canEvidence ? "evidence" :
        canSupplierJobs ? "supplier-jobs" :
        canCarJobs ? "car-jobs" : "dispatch"
      } className="space-y-4">
        <TabsList className="bg-card border border-border !h-auto flex-wrap w-full justify-start gap-y-1">
          {canDailyDispatch && (
            <TabsTrigger
              value="dispatch"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <CalendarDays className="h-3.5 w-3.5" />
              {t("reports.dailyDispatch")}
            </TabsTrigger>
          )}
          {canDriverTrips && (
            <TabsTrigger
              value="drivers"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Car className="h-3.5 w-3.5" />
              {t("reports.driverTrips")}
            </TabsTrigger>
          )}
          {canDriverScore && (
            <TabsTrigger
              value="driver-score"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Car className="h-3.5 w-3.5" />
              Driver Score
            </TabsTrigger>
          )}
          {canAgentStatement && (
            <TabsTrigger
              value="agent"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Building2 className="h-3.5 w-3.5" />
              {t("reports.agentStatement")}
            </TabsTrigger>
          )}
          {canRepFees && (
            <TabsTrigger
              value="rep-fees"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <UserCheck className="h-3.5 w-3.5" />
              {t("reports.repFees")}
            </TabsTrigger>
          )}
          {canRepScore && (
            <TabsTrigger
              value="rep-score"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <UserCheck className="h-3.5 w-3.5" />
              Rep Score
            </TabsTrigger>
          )}
          {canGuestSurveys && (
            <TabsTrigger
              value="guest-surveys"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              Guest Surveys
            </TabsTrigger>
          )}
          {canRevenue && (
            <TabsTrigger
              value="revenue"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <DollarSign className="h-3.5 w-3.5" />
              {t("reports.revenue")}
            </TabsTrigger>
          )}
          {canVehicleCompliance && (
            <TabsTrigger
              value="compliance"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              {t("reports.vehicleCompliance")}
            </TabsTrigger>
          )}
          {canJobStatus && (
            <TabsTrigger
              value="job-status"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              {t("reports.jobStatus")}
            </TabsTrigger>
          )}
          {canEvidence && (
            <TabsTrigger
              value="evidence"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Camera className="h-3.5 w-3.5" />
              Evidence
            </TabsTrigger>
          )}
          {canSupplierJobs && (
            <TabsTrigger
              value="supplier-jobs"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Truck className="h-3.5 w-3.5" />
              Supplier Jobs
            </TabsTrigger>
          )}
          {canCarJobs && (
            <TabsTrigger
              value="car-jobs"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Car className="h-3.5 w-3.5" />
              Car Jobs
            </TabsTrigger>
          )}
          {canVisa && (
            <TabsTrigger
              value="visa"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Visa
            </TabsTrigger>
          )}
          {canSales && (
            <TabsTrigger
              value="sales"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <DollarSign className="h-3.5 w-3.5" />
              Sales
            </TabsTrigger>
          )}
          {canDeparture && (
            <TabsTrigger
              value="departure"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <Plane className="h-3.5 w-3.5" />
              Departure
            </TabsTrigger>
          )}
          {canFlightDelay && (
            <TabsTrigger
              value="flight-delay"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              Flight Delay
            </TabsTrigger>
          )}
          {canReview && (
            <TabsTrigger
              value="review"
              className="gap-1.5 whitespace-nowrap data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              Review
            </TabsTrigger>
          )}
        </TabsList>

        {/* ─── DAILY DISPATCH SUMMARY ─── */}
        {canDailyDispatch && <TabsContent value="dispatch" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3">
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.date")}</Label>
                <Input
                  type="date"
                  value={dispatchDate}
                  onChange={(e) => setDispatchDate(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <Button
                onClick={fetchDispatch}
                disabled={dispatchLoading}
                className="gap-1.5"
              >
                {dispatchLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {t("reports.generate")}
              </Button>
              {dispatchData && (
                <>
                  <Button variant="outline" onClick={exportDispatchExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                  <Button variant="outline" onClick={exportDispatchPdf} className="gap-1.5 border-border text-foreground">
                    <Printer className="h-4 w-4" /> {t("reports.pdf")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {dispatchData && (
            <>
              <div className="grid grid-cols-8 gap-1.5">
                <StatCard
                  label={t("reports.totalJobs")}
                  value={dispatchData.totalJobs}
                />
                <StatCard
                  label={t("reports.assigned")}
                  value={dispatchData.assignedCount}
                  sub={`${dispatchData.assignmentRate}%`}
                  color="text-blue-600 dark:text-blue-400"
                />
                <StatCard
                  label={t("reports.unassigned")}
                  value={dispatchData.unassignedCount}
                  color="text-amber-600 dark:text-amber-400"
                />
                <StatCard
                  label={t("reports.completionRate")}
                  value={`${dispatchData.completionRate}%`}
                  color="text-emerald-600 dark:text-emerald-400"
                />
                {Object.entries(dispatchData.byServiceType).map(([type, count]) => (
                  <StatCard key={type} label={type} value={count} />
                ))}
                {Object.entries(dispatchData.byStatus).map(([status, count]) => (
                  <StatCard key={status} label={status} value={count} />
                ))}
              </div>

              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={DISPATCH_COLUMNS} visibility={dispatchColOrder.visibility} onSave={dispatchColOrder.saveVisibility} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <DraggableTableHeader
                    columns={DISPATCH_COLUMNS}
                    columnOrder={dispatchColOrder.columns}
                    onReorder={dispatchColOrder.reorder}
                    visibility={dispatchColOrder.visibility}
                  />
                  <TableBody>
                    {dispatchSort.sortedData.map((job, idx) => (
                      <TableRow
                        key={job.id}
                        className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                      >
                        {dispatchColOrder.columns.filter((col) => dispatchColOrder.visibility[col] !== false).map((col) => {
                          switch (col) {
                            case "internalRef": return <TableCell key={col} className="text-foreground font-mono text-xs">{job.internalRef}</TableCell>;
                            case "serviceType": return <TableCell key={col} className="text-muted-foreground text-sm">{serviceTypeLabel(job.serviceType)}</TableCell>;
                            case "agent": return <TableCell key={col} className="text-muted-foreground text-sm">{job.agent?.legalName || job.customer?.legalName || "\u2014"}</TableCell>;
                            case "paxCount": return <TableCell key={col} className="text-muted-foreground">{job.paxCount}</TableCell>;
                            case "vehicle": return <TableCell key={col} className="text-muted-foreground text-sm">{job.assignment?.vehicle?.plateNumber || "\u2014"}</TableCell>;
                            case "driver": return <TableCell key={col} className="text-muted-foreground text-sm">{job.assignment?.driver?.name || "\u2014"}</TableCell>;
                            case "status": return <TableCell key={col}><StatusBadge status={job.status} /></TableCell>;
                            default: return null;
                          }
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>}

        {/* ─── DRIVER TRIP REPORT ─── */}
        {canDriverTrips && <TabsContent value="drivers" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3">
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                <Input
                  type="date"
                  value={driverFrom}
                  onChange={(e) => setDriverFrom(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                <Input
                  type="date"
                  value={driverTo}
                  onChange={(e) => setDriverTo(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <Button
                onClick={fetchDriverTrips}
                disabled={driverLoading}
                className="gap-1.5"
              >
                {driverLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {t("reports.generate")}
              </Button>
              <Button
                variant="outline"
                onClick={recalculateDriverFees}
                disabled={recalcLoading}
                className="gap-1.5 border-border text-foreground"
                title="Recalculate missing driver trip fees from tariffs"
              >
                {recalcLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Recalc Fees
              </Button>
              {driverData && (
                <>
                  <Button variant="outline" onClick={exportDriverTripsExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                  <Button variant="outline" onClick={exportDriverTripsPdf} className="gap-1.5 border-border text-foreground">
                    <Printer className="h-4 w-4" /> {t("reports.pdf")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {driverData && (
            <>
              <div className="flex gap-1.5 flex-wrap">
                <StatCard label={t("reports.drivers")} value={driverData.totalDrivers} />
                <StatCard
                  label={t("reports.totalTrips")}
                  value={driverData.totalTrips}
                  color="text-blue-600 dark:text-blue-400"
                />
                <StatCard
                  label={t("reports.avgTripsDriver")}
                  value={
                    driverData.totalDrivers > 0
                      ? (driverData.totalTrips / driverData.totalDrivers).toFixed(1)
                      : "0"
                  }
                  color="text-emerald-600 dark:text-emerald-400"
                />
                <StatCard
                  label="Missing Scores"
                  value={driverData.drivers.reduce((s, d) => s + d.missingScores, 0)}
                  color="text-amber-600 dark:text-amber-400"
                />
              </div>

              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={DRIVERS_COLUMNS} visibility={driversColOrder.visibility} onSave={driversColOrder.saveVisibility} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <DraggableTableHeader
                    columns={DRIVERS_COLUMNS}
                    columnOrder={driversColOrder.columns}
                    onReorder={driversColOrder.reorder}
                    visibility={driversColOrder.visibility}
                  />
                  <TableBody>
                    {driverSort.sortedData.map((d, idx) => (
                      <TableRow
                        key={d.driver.id}
                        className={`border-border cursor-pointer hover:bg-muted/50 ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                      >
                        {driversColOrder.columns.filter((col) => driversColOrder.visibility[col] !== false).map((col) => {
                          switch (col) {
                            case "driverName": return (
                              <TableCell key={col}>
                                <button
                                  type="button"
                                  className="text-primary hover:underline font-medium text-sm text-left"
                                  onClick={() => {
                                    setSelectedDriver(d);
                                    const initialEdits: Record<string, DriverJobScore> = {};
                                    for (const trip of d.trips) {
                                      if (trip.driverJobScore) initialEdits[trip.jobId] = trip.driverJobScore;
                                    }
                                    setDriverScoreEdits(initialEdits);
                                    setDriverModalOpen(true);
                                  }}
                                >
                                  {d.driver.name}
                                </button>
                              </TableCell>
                            );
                            case "mobile": return <TableCell key={col} className="text-muted-foreground text-sm">{d.driver.mobileNumber}</TableCell>;
                            case "trips": return <TableCell key={col} className="text-right text-foreground font-mono font-medium">{d.tripCount}</TableCell>;
                            case "avgScore": return (
                              <TableCell key={col} className="text-right font-mono font-medium">
                                {d.avgScore !== null ? (
                                  <span className={
                                    d.avgScore >= 81 ? "text-emerald-600 dark:text-emerald-400" :
                                    d.avgScore >= 63 ? "text-blue-600 dark:text-blue-400" :
                                    d.avgScore >= 45 ? "text-amber-600 dark:text-amber-400" :
                                    "text-red-600 dark:text-red-400"
                                  }>{d.avgScore}</span>
                                ) : <span className="text-muted-foreground">—</span>}
                              </TableCell>
                            );
                            case "missing": return (
                              <TableCell key={col} className="text-right font-mono font-medium">
                                {d.missingScores > 0 ? (
                                  <span className="text-amber-600 dark:text-amber-400">{d.missingScores}</span>
                                ) : (
                                  <span className="text-emerald-600 dark:text-emerald-400">0</span>
                                )}
                              </TableCell>
                            );
                            case "totalFees": return <TableCell key={col} className="text-right text-emerald-600 dark:text-emerald-400 font-mono font-medium">{fmt(d.totalFees, locale)}</TableCell>;
                            default: return null;
                          }
                        })}
                      </TableRow>
                    ))}
                    {driverData.drivers.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={driversColOrder.columns.filter((c) => driversColOrder.visibility[c] !== false).length} className="text-center text-muted-foreground py-8">
                          {t("reports.noDriverTrips")}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>}

        {/* ─── DRIVER SCORE REPORT ─── */}
        {canDriverScore && (
          <TabsContent value="driver-score" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={driverScoreFrom}
                    onChange={(e) => setDriverScoreFrom(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm w-36"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={driverScoreTo}
                    onChange={(e) => setDriverScoreTo(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm w-36"
                  />
                </div>
                <div className="min-w-[180px]">
                  <Label className="text-muted-foreground text-xs">Driver Name</Label>
                  <Select value={driverScoreDriverId} onValueChange={setDriverScoreDriverId}>
                    <SelectTrigger className="border-border bg-muted/50 mt-0.5 h-8 text-sm">
                      <SelectValue placeholder="All Drivers" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Drivers</SelectItem>
                      {driverList.map((d) => (
                        <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" onClick={fetchDriverScore} disabled={driverScoreLoading} className="gap-1.5">
                  {driverScoreLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  {t("common.search")}
                </Button>
                {driverScoreData && (
                  <>
                    <Button size="sm" variant="outline" onClick={exportDriverScorePdf} className="gap-1.5 ml-auto">
                      <Printer className="h-3.5 w-3.5" />
                      {t("reports.exportPdf")}
                    </Button>
                    <Button size="sm" variant="outline" onClick={exportDriverScoreExcel} className="gap-1.5">
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      {t("reports.excel")}
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {driverScoreLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : driverScoreData ? (
              <Card className="border-border bg-card p-4">
                {/* Summary row */}
                <div className="mb-4 flex flex-wrap gap-4">
                  <div className="rounded-lg border border-border bg-muted/20 px-4 py-2">
                    <p className="text-xs text-muted-foreground">Jobs Scored</p>
                    <p className="text-lg font-bold text-foreground">{driverScoreData.count}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/20 px-4 py-2">
                    <p className="text-xs text-muted-foreground">Total Score</p>
                    <p className="text-lg font-bold text-foreground">{driverScoreData.totalScore}</p>
                  </div>
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2">
                    <p className="text-xs text-muted-foreground">Average Score</p>
                    <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{driverScoreData.avgScore} / 100</p>
                  </div>
                </div>

                {driverScoreData.rows.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">No scored jobs found for this period.</p>
                ) : (
                  <>
                  <div className="flex justify-end mb-2">
                    <ColumnVisibilityControl columns={DRIVER_SCORE_COLUMNS} visibility={driverScoreColOrder.visibility} onSave={driverScoreColOrder.saveVisibility} />
                  </div>
                  <div className="overflow-x-auto [overflow-y:clip]">
                    <Table>
                      <DraggableTableHeader
                        columns={DRIVER_SCORE_COLUMNS}
                        columnOrder={driverScoreColOrder.columns}
                        onReorder={driverScoreColOrder.reorder}
                        visibility={driverScoreColOrder.visibility}
                      />
                      <TableBody>
                        {driverScoreData.rows.map((row, idx) => {
                          const evalColor =
                            row.evaluation === "Excellent" ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" :
                            row.evaluation === "Good" ? "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20" :
                            row.evaluation === "Average" ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20" :
                            "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20";
                          const check = <span className="text-emerald-500 font-bold text-sm">✓</span>;
                          const dash  = <span className="text-muted-foreground text-sm">—</span>;
                          return (
                            <TableRow key={row.jobId} className={idx % 2 === 0 ? "bg-muted/10" : ""}>
                              {driverScoreColOrder.columns.filter((col) => driverScoreColOrder.visibility[col] !== false).map((col) => {
                                switch (col) {
                                  case "internalRef": return <TableCell key={col} className="font-mono text-xs">{row.internalRef}</TableCell>;
                                  case "jobDate": return <TableCell key={col} className="text-xs text-muted-foreground whitespace-nowrap">{new Date(row.jobDate).toLocaleDateString()}</TableCell>;
                                  case "serviceType": return <TableCell key={col}><Badge variant="outline" className="text-xs">{serviceTypeLabel(row.serviceType)}</Badge></TableCell>;
                                  case "paxCount": return <TableCell key={col} className="text-right text-xs text-muted-foreground">{row.paxCount}</TableCell>;
                                  case "driverName": return <TableCell key={col} className="text-xs text-muted-foreground">{row.driverName}</TableCell>;
                                  case "route": return <TableCell key={col} className="text-xs text-muted-foreground whitespace-nowrap">{row.route}</TableCell>;
                                  case "status": return <TableCell key={col}><StatusBadge status={row.status} /></TableCell>;
                                  case "attendance": return <TableCell key={col} className="text-center">{row.attendance ? check : dash}</TableCell>;
                                  case "appearance": return <TableCell key={col} className="text-center">{row.appearance ? check : dash}</TableCell>;
                                  case "carCleanliness": return <TableCell key={col} className="text-center">{row.carCleanliness ? check : dash}</TableCell>;
                                  case "maintenance": return <TableCell key={col} className="text-center">{row.maintenance ? check : dash}</TableCell>;
                                  case "work": return <TableCell key={col} className="text-center">{row.work ? check : dash}</TableCell>;
                                  case "total": return <TableCell key={col} className="text-right font-mono font-semibold text-sm">{row.total}</TableCell>;
                                  case "feePercent": return (
                                    <TableCell key={col} className="text-right font-mono text-sm">
                                      <span className={
                                        row.feePercent === 100 ? "text-emerald-600 dark:text-emerald-400 font-semibold" :
                                        row.feePercent >= 80 ? "text-blue-600 dark:text-blue-400" :
                                        row.feePercent >= 60 ? "text-amber-600 dark:text-amber-400" :
                                        "text-red-600 dark:text-red-400"
                                      }>{row.feePercent}%</span>
                                    </TableCell>
                                  );
                                  case "evaluation": return <TableCell key={col}><Badge variant="outline" className={`text-xs ${evalColor}`}>{row.evaluation}</Badge></TableCell>;
                                  default: return null;
                                }
                              })}
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                    <div className="mt-3 flex items-center justify-between border-t border-border pt-3 px-1">
                      <span className="text-sm text-muted-foreground">
                        {driverScoreData.count} job{driverScoreData.count !== 1 ? "s" : ""} scored · Total {driverScoreData.totalScore} pts
                      </span>
                      <span className="text-base font-medium text-emerald-600 dark:text-emerald-400">
                        Average: {driverScoreData.avgScore} / 100
                      </span>
                    </div>
                  </div>
                  </>
                )}
              </Card>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Car className="mb-2 h-8 w-8" />
                <p className="text-sm">Select a date range and click Search to view driver scores.</p>
              </div>
            )}

            {/* Hidden print content */}
            {driverScoreData && (
              <div ref={driverScorePrintRef} className="hidden">
                <h1>Driver Score Report</h1>
                <h2>Period: {driverScoreFrom} to {driverScoreTo}</h2>
                <dl className="info-grid">
                  <dt>Jobs Scored</dt><dd>{driverScoreData.count}</dd>
                  <dt>Total Score</dt><dd>{driverScoreData.totalScore}</dd>
                  <dt>Average Score</dt><dd>{driverScoreData.avgScore} / 100</dd>
                </dl>
                <table>
                  <thead>
                    <tr>
                      <th>Job Ref</th><th>Date</th><th>Type</th><th>Pax</th><th>Driver</th><th>Route</th><th>Status</th>
                      <th>Att (30)</th><th>App (20)</th><th>Car (10)</th><th>Maint (10)</th><th>Work (30)</th>
                      <th>Score</th><th>Fee %</th><th>Evaluation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {driverScoreData.rows.map((row) => (
                      <tr key={row.jobId}>
                        <td>{row.internalRef}</td>
                        <td>{new Date(row.jobDate).toLocaleDateString()}</td>
                        <td>{serviceTypeLabel(row.serviceType)}</td>
                        <td className="text-right">{row.paxCount}</td>
                        <td>{row.driverName}</td>
                        <td>{row.route}</td>
                        <td>{row.status}</td>
                        <td className="text-center">{row.attendance ? "✓" : "—"}</td>
                        <td className="text-center">{row.appearance ? "✓" : "—"}</td>
                        <td className="text-center">{row.carCleanliness ? "✓" : "—"}</td>
                        <td className="text-center">{row.maintenance ? "✓" : "—"}</td>
                        <td className="text-center">{row.work ? "✓" : "—"}</td>
                        <td className="text-right">{row.total}</td>
                        <td className="text-right">{row.feePercent}%</td>
                        <td>{row.evaluation}</td>
                      </tr>
                    ))}
                    <tr className="total-row">
                      <td colSpan={13}>Average Score ({driverScoreData.count} jobs)</td>
                      <td className="text-right">{driverScoreData.avgScore}</td>
                      <td></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
        )}

        {/* ─── AGENT STATEMENT ─── */}
        {canAgentStatement && <TabsContent value="agent" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3 flex-wrap">
              <div className="min-w-48">
                <Label className="text-muted-foreground text-xs">{t("dispatch.agent")}</Label>
                <Select
                  value={selectedAgentId}
                  onValueChange={setSelectedAgentId}
                >
                  <SelectTrigger className="mt-1 border-border bg-card text-foreground">
                    <SelectValue placeholder={t("reports.selectAgent")} />
                  </SelectTrigger>
                  <SelectContent>
                    {agents.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {a.legalName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                <Input
                  type="date"
                  value={agentFrom}
                  onChange={(e) => setAgentFrom(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                <Input
                  type="date"
                  value={agentTo}
                  onChange={(e) => setAgentTo(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <Button
                onClick={fetchAgentStatement}
                disabled={agentLoading}
                className="gap-1.5"
              >
                {agentLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {t("reports.generate")}
              </Button>
              {agentData && (
                <>
                  <Button variant="outline" onClick={exportAgentStatementExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                  <Button variant="outline" onClick={exportAgentStatementPdf} className="gap-1.5 border-border text-foreground">
                    <Printer className="h-4 w-4" /> {t("reports.pdf")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {agentData && (
            <>
              <Card className="border-border bg-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-medium text-foreground">
                      {agentData.agent.legalName}
                    </h3>
                    {agentData.agent.tradeName && (
                      <p className="text-sm text-muted-foreground">
                        {agentData.agent.tradeName}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    {agentData.agent.creditLimit !== null && (
                      <p className="text-xs text-muted-foreground">
                        {t("reports.creditLimit")}{" "}
                        <span className="text-foreground">
                          {fmt(agentData.agent.creditLimit, locale)}{" "}
                          {agentData.agent.currency}
                        </span>
                      </p>
                    )}
                    {agentData.agent.creditDays !== null && (
                      <p className="text-xs text-muted-foreground">
                        {t("reports.creditDays")}{" "}
                        <span className="text-foreground">
                          {agentData.agent.creditDays}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              </Card>

              <div className="flex gap-1.5 flex-wrap">
                <StatCard label={t("reports.jobs")} value={agentData.jobCount} />
                <StatCard
                  label={t("reports.totalInvoiced")}
                  value={fmt(agentData.totalInvoiced, locale)}
                  color="text-blue-600 dark:text-blue-400"
                />
                <StatCard
                  label={t("reports.totalPaid")}
                  value={fmt(agentData.totalPaid, locale)}
                  color="text-emerald-600 dark:text-emerald-400"
                />
                <StatCard
                  label={t("reports.outstanding")}
                  value={fmt(agentData.outstandingBalance, locale)}
                  color={
                    agentData.outstandingBalance > 0
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-emerald-600 dark:text-emerald-400"
                  }
                />
              </div>

              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={AGENT_COLUMNS} visibility={agentColOrder.visibility} onSave={agentColOrder.saveVisibility} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <DraggableTableHeader
                    columns={AGENT_COLUMNS}
                    columnOrder={agentColOrder.columns}
                    onReorder={agentColOrder.reorder}
                    visibility={agentColOrder.visibility}
                  />
                  <TableBody>
                    {agentSort.sortedData.map((inv, idx) => (
                      <TableRow
                        key={inv.invoiceNumber}
                        className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                      >
                        {agentColOrder.columns.filter((col) => agentColOrder.visibility[col] !== false).map((col) => {
                          switch (col) {
                            case "invoiceNumber": return <TableCell key={col} className="text-foreground font-mono text-xs">{inv.invoiceNumber}</TableCell>;
                            case "invoiceDate": return <TableCell key={col} className="text-muted-foreground text-sm">{formatDate(inv.invoiceDate)}</TableCell>;
                            case "dueDate": return <TableCell key={col} className="text-muted-foreground text-sm">{formatDate(inv.dueDate)}</TableCell>;
                            case "total": return <TableCell key={col} className="text-right text-foreground font-mono font-medium">{fmt(inv.total, locale)}</TableCell>;
                            case "paid": return <TableCell key={col} className="text-right text-emerald-600 dark:text-emerald-400 font-mono font-medium">{fmt(inv.paid, locale)}</TableCell>;
                            case "balance": return <TableCell key={col} className="text-right text-amber-600 dark:text-amber-400 font-mono font-medium">{fmt(inv.balance, locale)}</TableCell>;
                            case "status": return <TableCell key={col}><StatusBadge status={inv.status} /></TableCell>;
                            default: return null;
                          }
                        })}
                      </TableRow>
                    ))}
                    {agentData.invoices.length === 0 && (
                      <TableRow>
                        <TableCell
                          colSpan={agentColOrder.columns.filter((c) => agentColOrder.visibility[c] !== false).length}
                          className="text-center text-muted-foreground py-8"
                        >
                          {t("reports.noInvoices")}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>}

        {/* ─── REP FEES REPORT ─── */}
        {canRepFees && <TabsContent value="rep-fees" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3 flex-wrap">
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                <Input
                  type="date"
                  value={repFeeFrom}
                  onChange={(e) => {
                    setRepFeeFrom(e.target.value);
                    if (e.target.value > repFeeTo) setRepFeeTo(e.target.value);
                  }}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                <Input
                  type="date"
                  value={repFeeTo}
                  min={repFeeFrom}
                  onChange={(e) => setRepFeeTo(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <Button
                onClick={fetchRepFees}
                disabled={repFeeLoading}
                className="gap-1.5"
              >
                {repFeeLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {t("reports.generate")}
              </Button>
              {repFeeData && (
                <>
                  <Button
                    variant="outline"
                    onClick={exportRepFeesExcel}
                    className="gap-1.5 border-border text-foreground"
                  >
                    <FileSpreadsheet className="h-4 w-4" />
                    {t("reports.excel")}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={exportRepFeesPdf}
                    className="gap-1.5 border-border text-foreground"
                  >
                    <Printer className="h-4 w-4" />
                    {t("reports.pdf")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {repFeeData && (
            <>
              <div className="flex gap-1.5 flex-wrap">
                <StatCard
                  label={t("reports.totalReps")}
                  value={repFeeData.reps.length}
                />
                <StatCard
                  label={t("reports.totalFlights")}
                  value={repFeeData.totalFlights}
                  color="text-blue-600 dark:text-blue-400"
                />
                <StatCard
                  label={t("reports.grandTotal")}
                  value={`${fmt(repFeeData.grandTotal, locale)} EGP`}
                  color="text-emerald-600 dark:text-emerald-400"
                />
              </div>

              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={REP_FEES_COLUMNS} visibility={repFeesColOrder.visibility} onSave={repFeesColOrder.saveVisibility} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <DraggableTableHeader
                    columns={REP_FEES_COLUMNS}
                    columnOrder={repFeesColOrder.columns}
                    onReorder={repFeesColOrder.reorder}
                    visibility={repFeesColOrder.visibility}
                  />
                  <TableBody>
                    {repFeeSort.sortedData.map((rep, idx) => (
                      <TableRow
                        key={rep.repId}
                        className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                      >
                        {repFeesColOrder.columns.filter((col) => repFeesColOrder.visibility[col] !== false).map((col) => {
                          switch (col) {
                            case "repName": return (
                              <TableCell key={col}>
                                <button
                                  type="button"
                                  className="text-primary hover:underline font-medium text-sm text-left"
                                  onClick={() => {
                                    setSelectedRep(rep);
                                    const initialEdits: Record<string, RepJobScore> = {};
                                    for (const fee of rep.fees) {
                                      if (fee.repJobScore) {
                                        initialEdits[fee.trafficJob.id] = fee.repJobScore;
                                      }
                                    }
                                    setScoreEdits(initialEdits);
                                    setRepModalOpen(true);
                                  }}
                                >
                                  {rep.repName}
                                </button>
                              </TableCell>
                            );
                            case "feePerFlight": return <TableCell key={col} className="text-right text-muted-foreground font-mono font-medium">{fmt(rep.feePerFlight, locale)}</TableCell>;
                            case "flightCount": return <TableCell key={col} className="text-right text-foreground font-mono font-medium">{groupByFlight(rep.fees).length}</TableCell>;
                            case "totalAmount": return <TableCell key={col} className="text-right text-emerald-600 dark:text-emerald-400 font-mono font-medium">{fmt(repNetTotals[rep.repId] ?? rep.totalAmount, locale)}</TableCell>;
                            default: return null;
                          }
                        })}
                      </TableRow>
                    ))}
                    {repFeeData.reps.length === 0 && (
                      <TableRow>
                        <TableCell
                          colSpan={repFeesColOrder.columns.filter((c) => repFeesColOrder.visibility[c] !== false).length}
                          className="text-center text-muted-foreground py-8"
                        >
                          {t("reports.noRepFees")}
                        </TableCell>
                      </TableRow>
                    )}
                    {repFeeData.reps.length > 0 && (
                      <TableRow className="border-border bg-muted/50 font-semibold">
                        {repFeesColOrder.columns.filter((col) => repFeesColOrder.visibility[col] !== false).map((col) => {
                          switch (col) {
                            case "repName": return <TableCell key={col} className="text-foreground">{t("reports.grandTotal")}</TableCell>;
                            case "feePerFlight": return <TableCell key={col} />;
                            case "flightCount": return <TableCell key={col} className="text-right text-foreground font-mono font-medium">{repFeeData.totalFlights}</TableCell>;
                            case "totalAmount": return <TableCell key={col} className="text-right text-emerald-600 dark:text-emerald-400 font-mono font-medium">{fmt(repFeeData.grandTotal, locale)}</TableCell>;
                            default: return null;
                          }
                        })}
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>}

        {/* ─── REP SCORE REPORT ─── */}
        {canRepScore && (
          <TabsContent value="rep-score" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={repScoreFrom}
                    onChange={(e) => setRepScoreFrom(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm w-36"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={repScoreTo}
                    onChange={(e) => setRepScoreTo(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm w-36"
                  />
                </div>
                <div className="min-w-[180px]">
                  <Label className="text-muted-foreground text-xs">Rep Name</Label>
                  <Select value={repScoreRepId} onValueChange={setRepScoreRepId}>
                    <SelectTrigger className="border-border bg-muted/50 mt-0.5 h-8 text-sm">
                      <SelectValue placeholder="All Reps" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Reps</SelectItem>
                      {repList.map((r) => (
                        <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" onClick={fetchRepScore} disabled={repScoreLoading} className="gap-1.5">
                  {repScoreLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  {t("common.search")}
                </Button>
                {repScoreData && (
                  <>
                    <Button size="sm" variant="outline" onClick={exportRepScorePdf} className="gap-1.5 ml-auto">
                      <Printer className="h-3.5 w-3.5" />
                      {t("reports.exportPdf")}
                    </Button>
                    <Button size="sm" variant="outline" onClick={exportRepScoreExcel} className="gap-1.5">
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      {t("reports.excel")}
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {repScoreLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : repScoreData ? (
              <Card className="border-border bg-card p-4">
                <div className="mb-4 flex flex-wrap gap-4">
                  <div className="rounded-lg border border-border bg-muted/20 px-4 py-2">
                    <p className="text-xs text-muted-foreground">Jobs Scored</p>
                    <p className="text-lg font-bold text-foreground">{repScoreData.count}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/20 px-4 py-2">
                    <p className="text-xs text-muted-foreground">Total Score</p>
                    <p className="text-lg font-bold text-foreground">{repScoreData.totalScore}</p>
                  </div>
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2">
                    <p className="text-xs text-muted-foreground">Average Score</p>
                    <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{repScoreData.avgScore} / 100</p>
                  </div>
                </div>
                {repScoreData.rows.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">No scored jobs found for this period.</p>
                ) : (
                  <>
                  <div className="flex justify-end mb-2">
                    <ColumnVisibilityControl columns={REP_SCORE_COLUMNS} visibility={repScoreColOrder.visibility} onSave={repScoreColOrder.saveVisibility} />
                  </div>
                  <div className="overflow-x-auto [overflow-y:clip]">
                    {(() => {
                      const visibleCols = repScoreColOrder.columns.filter((col) => repScoreColOrder.visibility[col] !== false);
                      const colSpanAll = visibleCols.length;

                      // Group: rep → flight (same logic as Rep Fees modal groupByFlight)
                      const repMap = new Map<string, { repId: string; repName: string; rows: RepScoreRow[] }>();
                      for (const row of repScoreData.rows) {
                        if (!repMap.has(row.repId)) repMap.set(row.repId, { repId: row.repId, repName: row.repName, rows: [] });
                        repMap.get(row.repId)!.rows.push(row);
                      }
                      const repGroups = Array.from(repMap.values());

                      const flightGroupRows = (rows: RepScoreRow[]) => {
                        const fMap = new Map<string, { flightNo: string; carrier: string; rows: RepScoreRow[] }>();
                        for (const row of rows) {
                          const flightNo = row.flightNo?.trim() || "No Flight";
                          const carrier = row.carrier || "";
                          const key = `${flightNo}|${carrier}`;
                          if (!fMap.has(key)) fMap.set(key, { flightNo, carrier, rows: [] });
                          fMap.get(key)!.rows.push(row);
                        }
                        return Array.from(fMap.values());
                      };

                      const check = <span className="text-emerald-500 font-bold text-sm">✓</span>;
                      const dash = <span className="text-muted-foreground text-sm">—</span>;

                      return (
                        <div className="space-y-6">
                          {repGroups.map((repGroup) => {
                            const repTotal = repGroup.rows.reduce((s, r) => s + r.fee, 0);
                            const flightGroups = flightGroupRows(repGroup.rows);
                            return (
                              <div key={repGroup.repId}>
                                {/* Rep header — same style as Rep Fees list row */}
                                <div className="flex items-center justify-between px-3 py-2 mb-2 rounded-md bg-muted/50 border border-border">
                                  <span className="font-semibold text-sm text-foreground">{repGroup.repName}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {repGroup.rows.length} job{repGroup.rows.length !== 1 ? "s" : ""} &nbsp;·&nbsp;
                                    <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">{repTotal} EGP</span>
                                  </span>
                                </div>
                                {flightGroups.map((fGroup) => {
                                  const groupFee = fGroup.rows.reduce((s, r) => s + r.fee, 0);
                                  return (
                                    <div key={`${fGroup.flightNo}|${fGroup.carrier}`} className="mb-4">
                                      {/* Flight sub-header — same style as Rep Fees modal */}
                                      <div className="flex items-center gap-2 mb-1 px-1">
                                        <Badge variant="outline" className="bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20 font-mono text-xs">
                                          {fGroup.flightNo}
                                        </Badge>
                                        {fGroup.carrier && <span className="text-xs text-muted-foreground">{fGroup.carrier}</span>}
                                        <span className="text-xs text-muted-foreground">{fGroup.rows.length} job{fGroup.rows.length !== 1 ? "s" : ""}</span>
                                      </div>
                                      <Table>
                                        <DraggableTableHeader
                                          columns={REP_SCORE_COLUMNS}
                                          columnOrder={repScoreColOrder.columns}
                                          onReorder={repScoreColOrder.reorder}
                                          visibility={repScoreColOrder.visibility}
                                        />
                                        <TableBody>
                                          {fGroup.rows.map((row, idx) => {
                                            const evalColor =
                                              row.evaluation === "Excellent" ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" :
                                              row.evaluation === "Good" ? "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20" :
                                              row.evaluation === "Average" ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20" :
                                              "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20";
                                            return (
                                              <TableRow key={row.jobId} className={idx % 2 === 0 ? "bg-muted/10" : ""}>
                                                {visibleCols.map((col) => {
                                                  switch (col) {
                                                    case "internalRef": return <TableCell key={col} className="font-mono text-xs">{row.internalRef}</TableCell>;
                                                    case "flightNo": return <TableCell key={col} className="font-mono text-xs text-muted-foreground">{row.flightNo || "—"}</TableCell>;
                                                    case "serviceType": return <TableCell key={col}><Badge variant="outline" className="text-xs">{serviceTypeLabel(row.serviceType)}</Badge></TableCell>;
                                                    case "paxCount": return <TableCell key={col} className="text-right text-xs text-muted-foreground">{row.paxCount}</TableCell>;
                                                    case "repName": return <TableCell key={col} className="text-xs text-muted-foreground">{row.repName}</TableCell>;
                                                    case "route": return (
                                                      <TableCell key={col} className="text-xs text-muted-foreground whitespace-nowrap">
                                                        {(row.originAirport?.code || row.fromZone?.name || row.originZone?.name || row.originHotel?.name || "—")} → {(row.destinationAirport?.code || row.toZone?.name || row.destinationZone?.name || row.destinationHotel?.name || "—")}
                                                      </TableCell>
                                                    );
                                                    case "hotel": return <TableCell key={col} className="text-xs text-muted-foreground">{row.destinationHotel?.name || "—"}</TableCell>;
                                                    case "status": return <TableCell key={col}><StatusBadge status={row.status} /></TableCell>;
                                                    case "attendance": return <TableCell key={col} className="text-center">{row.attendance ? check : dash}</TableCell>;
                                                    case "appearance": return <TableCell key={col} className="text-center">{row.appearance ? check : dash}</TableCell>;
                                                    case "work": return <TableCell key={col} className="text-center">{row.work ? check : dash}</TableCell>;
                                                    case "review": return <TableCell key={col} className="text-center">{row.review ? check : dash}</TableCell>;
                                                    case "total": return <TableCell key={col} className="text-right font-mono font-semibold text-sm">{row.total}</TableCell>;
                                                    case "fee": return <TableCell key={col} className="text-right font-mono text-sm text-emerald-600 dark:text-emerald-400">{row.fee > 0 ? `${row.fee} EGP` : "—"}</TableCell>;
                                                    case "evaluation": return <TableCell key={col}><Badge variant="outline" className={`text-xs ${evalColor}`}>{row.evaluation}</Badge></TableCell>;
                                                    default: return null;
                                                  }
                                                })}
                                              </TableRow>
                                            );
                                          })}
                                          <TableRow className="bg-muted/30 border-t border-border">
                                            <TableCell colSpan={colSpanAll - 1} className="text-right text-xs text-muted-foreground py-1 pr-2">
                                              Subtotal ({fGroup.rows.length} job{fGroup.rows.length !== 1 ? "s" : ""})
                                            </TableCell>
                                            <TableCell className="text-right font-mono font-semibold text-sm text-emerald-600 dark:text-emerald-400 py-1">
                                              {groupFee} EGP
                                            </TableCell>
                                          </TableRow>
                                        </TableBody>
                                      </Table>
                                    </div>
                                  );
                                })}
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                    <div className="mt-3 flex items-center justify-between border-t border-border pt-3 px-1">
                      <span className="text-sm text-muted-foreground">
                        {repScoreData.count} job{repScoreData.count !== 1 ? "s" : ""} scored · Avg {repScoreData.avgScore} / 100
                      </span>
                      <span className="text-base font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                        Total: {repScoreData.totalFee ?? repScoreData.rows.reduce((s, r) => s + r.fee, 0)} EGP
                      </span>
                    </div>
                  </div>
                  </>
                )}
              </Card>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <UserCheck className="mb-2 h-8 w-8" />
                <p className="text-sm">Select a date range and click Search to view rep scores.</p>
              </div>
            )}
            {repScoreData && (
              <div ref={repScorePrintRef} className="hidden">
                <h1>Rep Score Report</h1>
                <h2>Period: {repScoreFrom} to {repScoreTo}</h2>
                <dl className="info-grid">
                  <dt>Jobs Scored</dt><dd>{repScoreData.count}</dd>
                  <dt>Total Score</dt><dd>{repScoreData.totalScore}</dd>
                  <dt>Average Score</dt><dd>{repScoreData.avgScore} / 100</dd>
                </dl>
                <table>
                  <thead>
                    <tr>
                      <th>Job Ref</th><th>Flight No</th><th>Type</th><th>Pax</th><th>Rep</th><th>Route</th><th>Hotel</th><th>Status</th>
                      <th>Att (20)</th><th>App (15)</th><th>Work (30)</th><th>Rev (35)</th><th>Score</th><th>Fee</th><th>Evaluation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      // Print: same rep → flight grouping as the on-screen view
                      const printRepMap = new Map<string, { repName: string; rows: RepScoreRow[] }>();
                      for (const row of repScoreData.rows) {
                        if (!printRepMap.has(row.repId)) printRepMap.set(row.repId, { repName: row.repName, rows: [] });
                        printRepMap.get(row.repId)!.rows.push(row);
                      }
                      return Array.from(printRepMap.values()).flatMap(({ repName, rows }) => {
                        const fMap = new Map<string, { flightNo: string; carrier: string; rows: RepScoreRow[] }>();
                        for (const row of rows) {
                          const flightNo = row.flightNo?.trim() || "No Flight";
                          const carrier = row.carrier || "";
                          const key = `${flightNo}|${carrier}`;
                          if (!fMap.has(key)) fMap.set(key, { flightNo, carrier, rows: [] });
                          fMap.get(key)!.rows.push(row);
                        }
                        return [
                          <tr key={`rep-${repName}`} style={{ background: "#4a0080", color: "#fff" }}>
                            <td colSpan={15} style={{ fontWeight: "bold", padding: "4px 8px" }}>{repName}</td>
                          </tr>,
                          ...Array.from(fMap.values()).flatMap((group) => [
                            <tr key={`${repName}-${group.flightNo}|${group.carrier}`} style={{ background: "#e8f0fe" }}>
                              <td colSpan={15} style={{ fontWeight: "bold", padding: "4px 8px" }}>
                                Flight: {group.flightNo}{group.carrier ? ` · ${group.carrier}` : ""} ({group.rows.length} job{group.rows.length !== 1 ? "s" : ""})
                              </td>
                            </tr>,
                            ...group.rows.map((row) => (
                              <tr key={row.jobId}>
                                <td>{row.internalRef}</td>
                                <td>{row.flightNo || "—"}</td>
                                <td>{serviceTypeLabel(row.serviceType)}</td>
                                <td className="text-right">{row.paxCount}</td>
                                <td>{row.repName}</td>
                                <td>{(row.originAirport?.code || row.fromZone?.name || row.originZone?.name || row.originHotel?.name || "—")} → {(row.destinationAirport?.code || row.toZone?.name || row.destinationZone?.name || row.destinationHotel?.name || "—")}</td>
                                <td>{row.destinationHotel?.name || "—"}</td>
                                <td>{row.status}</td>
                                <td className="text-center">{row.attendance ? "✓" : "—"}</td>
                                <td className="text-center">{row.appearance ? "✓" : "—"}</td>
                                <td className="text-center">{row.work ? "✓" : "—"}</td>
                                <td className="text-center">{row.review ? "✓" : "—"}</td>
                                <td className="text-right">{row.total}</td>
                                <td className="text-right">{row.fee > 0 ? `${row.fee} EGP` : "—"}</td>
                                <td>{row.evaluation}</td>
                              </tr>
                            )),
                            <tr key={`sub-${repName}-${group.flightNo}`} style={{ background: "#f5f5f5", fontWeight: "bold" }}>
                              <td colSpan={13} className="text-right">Subtotal</td>
                              <td className="text-right">{group.rows.reduce((s, r) => s + r.fee, 0)} EGP</td>
                              <td></td>
                            </tr>,
                          ]),
                        ];
                      });
                    })()}
                    <tr className="total-row">
                      <td colSpan={13}>Total ({repScoreData.count} jobs · Avg {repScoreData.avgScore} / 100)</td>
                      <td className="text-right">{repScoreData.totalFee ?? repScoreData.rows.reduce((s, r) => s + r.fee, 0)} EGP</td>
                      <td></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
        )}

        {/* ─── REVENUE REPORT ─── */}
        {canRevenue && <TabsContent value="revenue" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3">
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                <Input
                  type="date"
                  value={revenueFrom}
                  onChange={(e) => setRevenueFrom(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                <Input
                  type="date"
                  value={revenueTo}
                  onChange={(e) => setRevenueTo(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <Button
                onClick={fetchRevenue}
                disabled={revenueLoading}
                className="gap-1.5"
              >
                {revenueLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {t("reports.generate")}
              </Button>
              {revenueData && (
                <>
                  <Button variant="outline" onClick={exportRevenueExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                  <Button variant="outline" onClick={exportRevenuePdf} className="gap-1.5 border-border text-foreground">
                    <Printer className="h-4 w-4" /> {t("reports.pdf")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {revenueData && (
            <>
              <div className="flex gap-1.5 flex-wrap">
                <StatCard
                  label={t("reports.totalRevenue")}
                  value={fmt(revenueData.totalRevenue, locale)}
                  color="text-emerald-600 dark:text-emerald-400"
                />
                <StatCard
                  label={t("reports.totalCosts")}
                  value={fmt(revenueData.totalCosts, locale)}
                  color="text-red-600 dark:text-red-400"
                />
                <StatCard
                  label={t("reports.grossProfit")}
                  value={fmt(revenueData.grossProfit, locale)}
                  color={
                    revenueData.grossProfit >= 0
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-red-600 dark:text-red-400"
                  }
                />
                <StatCard
                  label={t("reports.profitMargin")}
                  value={`${revenueData.profitMargin}%`}
                  color={
                    revenueData.profitMargin >= 0
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-red-600 dark:text-red-400"
                  }
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Card className="border-border bg-card p-4">
                  <h4 className="text-sm font-medium text-muted-foreground mb-3">
                    {t("reports.costBreakdown")}
                  </h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">{t("reports.driverFees")}</span>
                      <span className="text-sm font-mono text-foreground">
                        {fmt(revenueData.costBreakdown.driverFees, locale)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">{t("reports.repFeesLabel")}</span>
                      <span className="text-sm font-mono text-foreground">
                        {fmt(revenueData.costBreakdown.repFees, locale)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">
                        {t("reports.supplierCosts")}
                      </span>
                      <span className="text-sm font-mono text-foreground">
                        {fmt(revenueData.costBreakdown.supplierCosts, locale)}
                      </span>
                    </div>
                  </div>
                </Card>

                <Card className="border-border bg-card p-4">
                  <h4 className="text-sm font-medium text-muted-foreground mb-3">
                    {t("reports.revenueByServiceType")}
                  </h4>
                  <div className="space-y-2">
                    {Object.entries(revenueData.byServiceType).map(
                      ([type, amount]) => (
                        <div key={type} className="flex justify-between">
                          <span className="text-sm text-muted-foreground">{type}</span>
                          <span className="text-sm font-mono text-foreground">
                            {fmt(amount, locale)}
                          </span>
                        </div>
                      )
                    )}
                    {Object.keys(revenueData.byServiceType).length === 0 && (
                      <p className="text-xs text-muted-foreground">{t("reports.noData")}</p>
                    )}
                  </div>
                </Card>
              </div>

              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted">
                      <SortableHeader label={t("dispatch.agent")} sortKey="name" currentKey={revenueSort.sortKey} currentDir={revenueSort.sortDir} onSort={revenueSort.onSort} />
                      <SortableHeader label={t("reports.revenueLabel")} sortKey="revenue" currentKey={revenueSort.sortKey} currentDir={revenueSort.sortDir} onSort={revenueSort.onSort} className="text-right" />
                      <SortableHeader label={t("reports.invoices")} sortKey="invoiceCount" currentKey={revenueSort.sortKey} currentDir={revenueSort.sortDir} onSort={revenueSort.onSort} className="text-right" />
                      <SortableHeader label={t("reports.jobs")} sortKey="jobCount" currentKey={revenueSort.sortKey} currentDir={revenueSort.sortDir} onSort={revenueSort.onSort} className="text-right" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {revenueSort.sortedData.map((a, idx) => (
                      <TableRow
                        key={a.agentId}
                        className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                      >
                        <TableCell className="text-foreground text-sm font-medium">
                          {a.name}
                        </TableCell>
                        <TableCell className="text-right text-emerald-600 dark:text-emerald-400 font-mono font-medium">
                          {fmt(a.revenue, locale)}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground font-mono font-medium">
                          {a.invoiceCount}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground font-mono font-medium">
                          {a.jobCount}
                        </TableCell>
                      </TableRow>
                    ))}
                    {revenueData.byAgent.length === 0 && (
                      <TableRow>
                        <TableCell
                          colSpan={4}
                          className="text-center text-muted-foreground py-8"
                        >
                          {t("reports.noRevenue")}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>}

        {/* ─── VEHICLE COMPLIANCE ─── */}
        {canVehicleCompliance && <TabsContent value="compliance" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3 flex-wrap">
              <Button
                size="sm"
                className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={fetchCompliance}
                disabled={complianceLoading}
              >
                {complianceLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                {t("reports.generate")}
              </Button>
              {complianceData.length > 0 && (
                <>
                  <Select value={complianceOwnershipFilter} onValueChange={setComplianceOwnershipFilter}>
                    <SelectTrigger className="w-[160px] h-8">
                      <SelectValue placeholder={t("vehicles.ownership")} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">{t("common.all")} Ownership</SelectItem>
                      <SelectItem value="OWNED">Owned</SelectItem>
                      <SelectItem value="RENTED">Rented</SelectItem>
                      <SelectItem value="CONTRACTED">External License</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={complianceTypeFilter} onValueChange={setComplianceTypeFilter}>
                    <SelectTrigger className="w-[160px] h-8">
                      <SelectValue placeholder={t("vehicles.type")} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">{t("common.all")} Types</SelectItem>
                      {complianceVehicleTypes.map((vt) => (
                        <SelectItem key={vt} value={vt}>{vt}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="sm" onClick={exportComplianceExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                  <Button variant="outline" size="sm" onClick={exportCompliancePdf} className="gap-1.5 border-border text-foreground">
                    <Printer className="h-4 w-4" /> {t("reports.pdf")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {complianceLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : complianceData.length > 0 ? (
            <>
              {/* Stat Cards */}
              <div className="flex gap-1.5 flex-wrap">
                <StatCard label={t("reports.totalVehicles")} value={filteredComplianceData.length} />
                <StatCard
                  label={t("reports.withInsurance")}
                  value={filteredComplianceData.filter((v) => v.hasInsurance).length}
                  color="text-emerald-600 dark:text-emerald-400"
                />
                <StatCard
                  label={t("reports.permitWarnings")}
                  value={filteredComplianceData.filter((v) => {
                    if (!v.temporaryPermitExpiryDate) return false;
                    const exp = new Date(v.temporaryPermitExpiryDate);
                    const now = new Date();
                    const oneMonth = new Date();
                    oneMonth.setMonth(oneMonth.getMonth() + 1);
                    return exp >= now && exp < oneMonth;
                  }).length}
                  color="text-amber-600 dark:text-amber-400"
                />
                <StatCard
                  label={t("reports.permitsExpired")}
                  value={filteredComplianceData.filter((v) => {
                    if (!v.temporaryPermitExpiryDate) return false;
                    return new Date(v.temporaryPermitExpiryDate) < new Date();
                  }).length}
                  color="text-red-600 dark:text-red-400"
                />
              </div>

              {/* Table */}
              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={COMPLIANCE_COLUMNS} visibility={complianceColOrder.visibility} onSave={complianceColOrder.saveVisibility} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted">
                      {complianceColOrder.visibility["plateNumber"] !== false && <SortableHeader label={t("vehicles.plateNumber")} sortKey="plateNumber" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["vehicleTypeName"] !== false && <SortableHeader label={t("vehicles.type")} sortKey="vehicleTypeName" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["ownership"] !== false && <SortableHeader label={t("vehicles.ownership")} sortKey="ownership" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["licenseExpiryDate"] !== false && <SortableHeader label={t("vehicles.licenseExpiryDate")} sortKey="licenseExpiryDate" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["insurance"] !== false && <TableHead className="text-muted-foreground text-xs">{t("vehicles.insurance")}</TableHead>}
                      {complianceColOrder.visibility["temporaryPermitDate"] !== false && <SortableHeader label={t("vehicles.temporaryPermit")} sortKey="temporaryPermitDate" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["permitExpiry"] !== false && <TableHead className="text-muted-foreground text-xs">{t("vehicles.permitExpiry")}</TableHead>}
                      {complianceColOrder.visibility["annualPayment"] !== false && <SortableHeader label={t("vehicles.annualPayment")} sortKey="annualPayment" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["registrationFees"] !== false && <TableHead className="text-muted-foreground text-xs">{t("vehicles.registrationFees")}</TableHead>}
                      {complianceColOrder.visibility["totalFees"] !== false && <SortableHeader label={t("vehicles.totalFees")} sortKey="totalFees" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["depositTotal"] !== false && <SortableHeader label={t("vehicles.totalDeposits")} sortKey="depositTotal" currentKey={complianceSort.sortKey} currentDir={complianceSort.sortDir} onSort={complianceSort.onSort} />}
                      {complianceColOrder.visibility["balanceRemaining"] !== false && <TableHead className="text-muted-foreground text-xs">{t("vehicles.balanceRemaining")}</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {complianceSort.sortedData.map((v, idx) => {
                      const permitExp = v.temporaryPermitExpiryDate ? new Date(v.temporaryPermitExpiryDate) : null;
                      const now = new Date();
                      const oneMonth = new Date();
                      oneMonth.setMonth(oneMonth.getMonth() + 1);
                      const isExpired = permitExp && permitExp < now;
                      const isWarning = permitExp && !isExpired && permitExp < oneMonth;

                      return (
                        <TableRow
                          key={`${v.vehicleId}-${idx}`}
                          className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                        >
                          {complianceColOrder.visibility["plateNumber"] !== false && <TableCell className="font-medium text-foreground">{v.plateNumber}</TableCell>}
                          {complianceColOrder.visibility["vehicleTypeName"] !== false && <TableCell className="text-muted-foreground">{v.vehicleTypeName}</TableCell>}
                          {complianceColOrder.visibility["ownership"] !== false && (
                            <TableCell>
                              <Badge variant="secondary" className="bg-secondary text-muted-foreground">{v.ownership}</Badge>
                            </TableCell>
                          )}
                          {complianceColOrder.visibility["licenseExpiryDate"] !== false && <TableCell className="text-muted-foreground">{v.licenseExpiryDate ? formatDate(v.licenseExpiryDate) : "—"}</TableCell>}
                          {complianceColOrder.visibility["insurance"] !== false && (
                            <TableCell>
                              {v.hasInsurance ? (
                                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">{t("common.yes")}</Badge>
                              ) : (
                                <Badge className="bg-red-500/20 text-red-600 dark:text-red-400">{t("common.no")}</Badge>
                              )}
                            </TableCell>
                          )}
                          {complianceColOrder.visibility["temporaryPermitDate"] !== false && <TableCell className="text-muted-foreground">{v.temporaryPermitDate ? formatDate(v.temporaryPermitDate) : "—"}</TableCell>}
                          {complianceColOrder.visibility["permitExpiry"] !== false && (
                            <TableCell>
                              {permitExp ? (
                                <div className="flex items-center gap-1.5">
                                  <span className="text-muted-foreground text-sm">{formatDate(v.temporaryPermitExpiryDate!)}</span>
                                  {isExpired && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
                                  {isWarning && <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />}
                                </div>
                              ) : "—"}
                            </TableCell>
                          )}
                          {complianceColOrder.visibility["annualPayment"] !== false && <TableCell className="text-muted-foreground">{v.annualPayment != null ? `${fmt(Number(v.annualPayment))} ${v.annualPaymentCurrency || ""}` : "—"}</TableCell>}
                          {complianceColOrder.visibility["registrationFees"] !== false && <TableCell className="text-muted-foreground">{v.registrationFees != null ? fmt(Number(v.registrationFees)) : "—"}</TableCell>}
                          {complianceColOrder.visibility["totalFees"] !== false && <TableCell className="text-muted-foreground font-medium">{v.totalFees != null ? fmt(Number(v.totalFees)) : "—"}</TableCell>}
                          {complianceColOrder.visibility["depositTotal"] !== false && <TableCell className="text-muted-foreground">{v.depositTotal != null ? fmt(Number(v.depositTotal)) : "—"}</TableCell>}
                          {complianceColOrder.visibility["balanceRemaining"] !== false && <TableCell className="text-muted-foreground">{v.balanceRemaining != null ? fmt(Number(v.balanceRemaining)) : "—"}</TableCell>}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <ShieldCheck className="mb-2 h-8 w-8" />
              <p className="text-sm">{t("reports.noComplianceData")}</p>
            </div>
          )}
        </TabsContent>}

        {/* ─── JOB STATUS REPORT ─── */}
        <TabsContent value="job-status" className="space-y-4">
          <Card className="border-border bg-card p-4">
            <div className="flex items-end gap-3 flex-wrap">
              <div>
                <Label className="text-muted-foreground text-xs">{t("reports.statusFilter")}</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="mt-1 w-48 justify-between border-border bg-card text-foreground font-normal">
                      <span className="truncate">
                        {jobStatusFilter.length === 0
                          ? t("reports.allStatuses")
                          : jobStatusFilter.map((s) => s.replace("_", " ")).join(", ")}
                      </span>
                      <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-48 p-2" align="start">
                    {(["PENDING","ASSIGNED","IN_PROGRESS","COMPLETED","CANCELLED","NO_SHOW"] as const).map((s) => (
                      <label key={s} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent">
                        <Checkbox
                          checked={jobStatusFilter.includes(s)}
                          onCheckedChange={(checked) =>
                            setJobStatusFilter((prev) =>
                              checked ? [...prev, s] : prev.filter((x) => x !== s)
                            )
                          }
                        />
                        {s.replace("_", " ")}
                      </label>
                    ))}
                    {jobStatusFilter.length > 0 && (
                      <Button variant="ghost" size="sm" className="mt-1 w-full text-xs" onClick={() => setJobStatusFilter([])}>
                        Clear
                      </Button>
                    )}
                  </PopoverContent>
                </Popover>
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("jobs.serviceType")}</Label>
                <Select value={jobStatusServiceType} onValueChange={setJobStatusServiceType}>
                  <SelectTrigger className="mt-1 w-36 border-border bg-card text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Types</SelectItem>
                    {SERVICE_TYPE_DROPDOWN_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("reports.repName")}</Label>
                <Select value={jobStatusRepId} onValueChange={setJobStatusRepId}>
                  <SelectTrigger className="mt-1 w-44 border-border bg-card text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">{t("reports.allReps")}</SelectItem>
                    {repList.map((r) => (
                      <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">Rep Status</Label>
                <Select value={jobStatusRepStatus} onValueChange={setJobStatusRepStatus}>
                  <SelectTrigger className="mt-1 w-40 border-border bg-card text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Rep Statuses</SelectItem>
                    <SelectItem value="PENDING">Pending</SelectItem>
                    <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                    <SelectItem value="IN_PLACE">In Place</SelectItem>
                    <SelectItem value="COMPLETED">Completed</SelectItem>
                    <SelectItem value="NO_SHOW">No Show</SelectItem>
                    <SelectItem value="CANCELLED">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">Driver Status</Label>
                <Select value={jobStatusDriverStatus} onValueChange={setJobStatusDriverStatus}>
                  <SelectTrigger className="mt-1 w-40 border-border bg-card text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Driver Statuses</SelectItem>
                    <SelectItem value="PENDING">Pending</SelectItem>
                    <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                    <SelectItem value="IN_PLACE">In Place</SelectItem>
                    <SelectItem value="COMPLETED">Completed</SelectItem>
                    <SelectItem value="NO_SHOW">No Show</SelectItem>
                    <SelectItem value="CANCELLED">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                <Input
                  type="date"
                  value={jobStatusFrom}
                  onChange={(e) => setJobStatusFrom(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                <Input
                  type="date"
                  value={jobStatusTo}
                  onChange={(e) => setJobStatusTo(e.target.value)}
                  className="mt-1 w-44 border-border bg-card text-foreground"
                />
              </div>
              <Button
                onClick={fetchJobStatus}
                disabled={jobStatusLoading}
                className="gap-1.5"
              >
                {jobStatusLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {t("reports.generate")}
              </Button>
              {jobStatusData && (
                <>
                  <Button variant="outline" onClick={exportJobStatusPdf} className="gap-1.5 border-border text-foreground">
                    <Printer className="h-4 w-4" /> {t("reports.pdf")}
                  </Button>
                  <Button variant="outline" onClick={exportJobStatusExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                </>
              )}
            </div>
          </Card>

          {jobStatusData ? (
            <>
              <div className="grid grid-cols-4 gap-1.5">
                <StatCard label={t("reports.totalJobs")} value={jobStatusData.totalJobs} />
                <StatCard
                  label="Completed"
                  value={jobStatusData.jobs.filter((j) => j.status === "COMPLETED").length}
                  color="text-emerald-600 dark:text-emerald-400"
                />
                <StatCard
                  label="Pending"
                  value={jobStatusData.jobs.filter((j) => j.status === "PENDING").length}
                  color="text-amber-600 dark:text-amber-400"
                />
                <StatCard
                  label="Cancelled"
                  value={jobStatusData.jobs.filter((j) => j.status === "CANCELLED").length}
                  color="text-red-600 dark:text-red-400"
                />
              </div>

              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={JOB_STATUS_COLUMNS} visibility={jobStatusColOrder.visibility} onSave={jobStatusColOrder.saveVisibility} />
              </div>
              <div ref={jobStatusPrintRef}>
                <div className="rounded-md border border-border overflow-x-auto [overflow-y:clip]">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border bg-muted">
                        {jobStatusColOrder.visibility["internalRef"] !== false && <SortableHeader label={t("reports.trsfReference")} sortKey="internalRef" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["agentRef"] !== false && <SortableHeader label={t("reports.agentRef")} sortKey="agentRef" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["agentName"] !== false && <SortableHeader label={t("agents.legalName")} sortKey="agentName" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["serviceDate"] !== false && <SortableHeader label={t("jobs.serviceDate")} sortKey="serviceDate" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["serviceType"] !== false && <SortableHeader label={t("jobs.serviceType")} sortKey="serviceType" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["time"] !== false && <SortableHeader label={t("jobs.time")} sortKey="time" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["driverName"] !== false && <SortableHeader label={t("dispatch.driverName")} sortKey="driverName" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["repName"] !== false && <SortableHeader label={t("reports.repName")} sortKey="repName" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["priceAmount"] !== false && <SortableHeader label={t("reports.applicationPrice")} sortKey="priceAmount" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} className="text-right" />}
                        {jobStatusColOrder.visibility["status"] !== false && <SortableHeader label={t("common.status")} sortKey="status" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["repJobStatus"] !== false && <SortableHeader label={t("reports.repJobStatus")} sortKey="repJobStatus" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["driverJobStatus"] !== false && <SortableHeader label={t("reports.driverJobStatus")} sortKey="driverJobStatus" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["flightNo"] !== false && <SortableHeader label="Flight No" sortKey="flightNo" currentKey={jobStatusSort.sortKey} currentDir={jobStatusSort.sortDir} onSort={jobStatusSort.onSort} />}
                        {jobStatusColOrder.visibility["evidence"] !== false && <TableHead className="text-muted-foreground font-semibold text-xs">{t("reports.driverEvidence")}</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {jobStatusSort.sortedData.map((job) => (
                        <TableRow key={job.id} className="border-border hover:bg-muted/30">
                          {jobStatusColOrder.visibility["internalRef"] !== false && (
                            <TableCell className="font-mono text-sm">
                              <button
                                type="button"
                                onClick={() => setJobDetailId(job.id)}
                                className="text-primary hover:underline font-mono text-sm"
                              >
                                {job.internalRef}
                              </button>
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["agentRef"] !== false && <TableCell className="text-muted-foreground text-sm">{job.agentRef || "\u2014"}</TableCell>}
                          {jobStatusColOrder.visibility["agentName"] !== false && <TableCell className="text-sm text-foreground">{job.agentName || "\u2014"}</TableCell>}
                          {jobStatusColOrder.visibility["serviceDate"] !== false && <TableCell className="text-sm text-muted-foreground whitespace-nowrap">{new Date(job.serviceDate).toLocaleDateString()}</TableCell>}
                          {jobStatusColOrder.visibility["serviceType"] !== false && <TableCell className="text-sm text-foreground">{serviceTypeLabel(job.serviceType)}</TableCell>}
                          {jobStatusColOrder.visibility["time"] !== false && (
                            <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                              {job.time ? new Date(job.time).toLocaleTimeString([], { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "\u2014"}
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["driverName"] !== false && <TableCell className="text-sm text-foreground">{job.driverName || "\u2014"}</TableCell>}
                          {jobStatusColOrder.visibility["repName"] !== false && <TableCell className="text-sm text-foreground">{job.repName || "\u2014"}</TableCell>}
                          {jobStatusColOrder.visibility["priceAmount"] !== false && (
                            <TableCell className="text-right font-mono font-medium text-sm text-foreground">
                              {job.transferPrice != null ? `${fmt(job.transferPrice, locale)} ${job.transferPriceCurrency || ""}` : (job.priceAmount != null ? `${fmt(job.priceAmount, locale)} ${job.priceCurrency || ""}` : "\u2014")}
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["status"] !== false && (
                            <TableCell>
                              <StatusBadge status={job.status} />
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["repJobStatus"] !== false && (
                            <TableCell>
                              {job.repJobStatus ? <StatusBadge status={job.repJobStatus} /> : "\u2014"}
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["driverJobStatus"] !== false && (
                            <TableCell>
                              {job.driverJobStatus ? <StatusBadge status={job.driverJobStatus} /> : "\u2014"}
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["flightNo"] !== false && (
                            <TableCell className="font-mono text-sm text-muted-foreground">
                              {job.flightNo || "\u2014"}
                            </TableCell>
                          )}
                          {jobStatusColOrder.visibility["evidence"] !== false && (
                            <TableCell>
                              {job.driverEvidence.length > 0 ? (
                                <button
                                  type="button"
                                  onClick={() => downloadDriverEvidencePdf(job)}
                                  disabled={evidencePdfLoading.has(job.id)}
                                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline disabled:opacity-50 disabled:cursor-wait"
                                >
                                  <Printer className="h-3.5 w-3.5" />
                                  {evidencePdfLoading.has(job.id) ? "Zipping…" : "ZIP"}
                                </button>
                              ) : (
                                <span className="text-muted-foreground text-xs">\u2014</span>
                              )}
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <ClipboardList className="mb-2 h-8 w-8" />
              <p className="text-sm">{t("reports.noJobStatusData")}</p>
            </div>
          )}
        </TabsContent>

        {/* ─── EVIDENCE REPORT ─── */}
        {canEvidence && (
          <TabsContent value="evidence" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={evidenceFrom}
                    onChange={(e) => setEvidenceFrom(e.target.value)}
                    className="mt-1 w-40 border-border bg-card text-foreground"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={evidenceTo}
                    onChange={(e) => setEvidenceTo(e.target.value)}
                    className="mt-1 w-40 border-border bg-card text-foreground"
                  />
                </div>
                <div className="min-w-[160px]">
                  <Label className="text-muted-foreground text-xs">{t("common.status")}</Label>
                  <Select value={evidenceStatusFilter} onValueChange={setEvidenceStatusFilter}>
                    <SelectTrigger className="mt-1 h-9 border-border bg-card text-foreground">
                      <SelectValue placeholder="All Statuses" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Statuses</SelectItem>
                      <SelectItem value="PENDING">Pending</SelectItem>
                      <SelectItem value="ASSIGNED">Assigned</SelectItem>
                      <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                      <SelectItem value="IN_PLACE">In Place</SelectItem>
                      <SelectItem value="COMPLETED">Completed</SelectItem>
                      <SelectItem value="CANCELLED">Cancelled</SelectItem>
                      <SelectItem value="NO_SHOW">No Show</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="min-w-[200px]">
                  <Label className="text-muted-foreground text-xs">Agent Name</Label>
                  <Select value={evidenceAgentId} onValueChange={setEvidenceAgentId}>
                    <SelectTrigger className="mt-1 h-9 border-border bg-card text-foreground">
                      <SelectValue placeholder="All Agents" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Agents</SelectItem>
                      {agents.map((a) => (
                        <SelectItem key={a.id} value={a.id}>{a.legalName}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="min-w-[180px]">
                  <Label className="text-muted-foreground text-xs">{t("reports.repName")}</Label>
                  <Select value={evidenceRepId} onValueChange={setEvidenceRepId}>
                    <SelectTrigger className="mt-1 h-9 border-border bg-card text-foreground">
                      <SelectValue placeholder={t("reports.allReps")} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">{t("reports.allReps")}</SelectItem>
                      {repList.map((r) => (
                        <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="min-w-[180px]">
                  <Label className="text-muted-foreground text-xs">{t("dispatch.driverName")}</Label>
                  <Select value={evidenceDriverId} onValueChange={setEvidenceDriverId}>
                    <SelectTrigger className="mt-1 h-9 border-border bg-card text-foreground">
                      <SelectValue placeholder="All Drivers" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Drivers</SelectItem>
                      {driverList.map((d) => (
                        <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={fetchEvidenceReport} disabled={evidenceLoading} className="gap-1.5">
                  {evidenceLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  {t("reports.generate")}
                </Button>
                {evidenceData && (
                  <Button variant="outline" onClick={exportEvidenceExcel} className="gap-1.5 border-border text-foreground">
                    <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                  </Button>
                )}
              </div>
            </Card>

            {evidenceLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : evidenceData ? (
              <>
                <div className="flex gap-1.5 flex-wrap">
                  <StatCard label={t("reports.totalJobs")} value={evidenceData.totalJobs} />
                  <StatCard
                    label="With Evidence"
                    value={evidenceData.rows.filter((r) => r.hasEvidence).length}
                    color="text-emerald-600 dark:text-emerald-400"
                  />
                  <StatCard
                    label="No Evidence"
                    value={evidenceData.rows.filter((r) => !r.hasEvidence).length}
                    color="text-amber-600 dark:text-amber-400"
                  />
                </div>
                <div className="flex justify-end mb-2">
                  <ColumnVisibilityControl columns={EVIDENCE_COLUMNS} visibility={evidenceColOrder.visibility} onSave={evidenceColOrder.saveVisibility} />
                </div>
                <div className="rounded-md border border-border overflow-x-auto [overflow-y:clip]">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border bg-muted">
                        {evidenceColOrder.visibility["internalRef"] !== false && <TableHead className="text-muted-foreground text-xs">Job Ref</TableHead>}
                        {evidenceColOrder.visibility["agentName"] !== false && <TableHead className="text-muted-foreground text-xs">Agent Name</TableHead>}
                        {evidenceColOrder.visibility["agentRef"] !== false && <TableHead className="text-muted-foreground text-xs">Agent Ref</TableHead>}
                        {evidenceColOrder.visibility["jobDate"] !== false && <TableHead className="text-muted-foreground text-xs">Date</TableHead>}
                        {evidenceColOrder.visibility["serviceType"] !== false && <TableHead className="text-muted-foreground text-xs">Type</TableHead>}
                        {evidenceColOrder.visibility["arrivalFlightTime"] !== false && <TableHead className="text-muted-foreground text-xs">Arr. Flight Time</TableHead>}
                        {evidenceColOrder.visibility["departurePickupTime"] !== false && <TableHead className="text-muted-foreground text-xs">Dep. Pickup Time</TableHead>}
                        {evidenceColOrder.visibility["status"] !== false && <TableHead className="text-muted-foreground text-xs">Status</TableHead>}
                        {evidenceColOrder.visibility["repName"] !== false && <TableHead className="text-muted-foreground text-xs">{t("reports.repName")}</TableHead>}
                        {evidenceColOrder.visibility["driverName"] !== false && <TableHead className="text-muted-foreground text-xs">{t("dispatch.driverName")}</TableHead>}
                        {evidenceColOrder.visibility["evidence"] !== false && <TableHead className="text-muted-foreground text-xs">Evidence</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {evidenceData.rows.map((row, idx) => {
                        const totalImages =
                          row.inPlaceEvidence.reduce((s, e) => s + e.imageUrls.length, 0) +
                          row.noShowEvidence.reduce((s, e) => s + e.imageUrls.length, 0) +
                          row.completedEvidence.reduce((s, e) => s + e.imageUrls.length, 0);
                        return (
                          <TableRow
                            key={row.jobId}
                            className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                          >
                            {evidenceColOrder.visibility["internalRef"] !== false && <TableCell className="font-mono text-sm text-foreground">{row.internalRef}</TableCell>}
                            {evidenceColOrder.visibility["agentName"] !== false && <TableCell className="text-sm text-muted-foreground">{row.agentName ?? "—"}</TableCell>}
                            {evidenceColOrder.visibility["agentRef"] !== false && <TableCell className="text-sm text-muted-foreground">{row.agentRef ?? "—"}</TableCell>}
                            {evidenceColOrder.visibility["jobDate"] !== false && <TableCell className="text-sm text-muted-foreground">{formatDate(row.jobDate)}</TableCell>}
                            {evidenceColOrder.visibility["serviceType"] !== false && (
                              <TableCell>
                                <Badge variant="outline" className="text-xs">{serviceTypeLabel(row.serviceType)}</Badge>
                              </TableCell>
                            )}
                            {evidenceColOrder.visibility["arrivalFlightTime"] !== false && (
                              <TableCell className="text-xs font-mono text-muted-foreground">
                                {row.flight?.arrivalTime ? new Date(row.flight.arrivalTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "—"}
                              </TableCell>
                            )}
                            {evidenceColOrder.visibility["departurePickupTime"] !== false && (
                              <TableCell className="text-xs font-mono text-muted-foreground">
                                {row.pickUpTime ? new Date(row.pickUpTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "—"}
                              </TableCell>
                            )}
                            {evidenceColOrder.visibility["status"] !== false && (
                              <TableCell>
                                <StatusBadge status={row.status} />
                              </TableCell>
                            )}
                            {evidenceColOrder.visibility["repName"] !== false && <TableCell className="text-sm text-foreground">{row.repName ?? "—"}</TableCell>}
                            {evidenceColOrder.visibility["driverName"] !== false && <TableCell className="text-sm text-foreground">{row.driverName ?? "—"}</TableCell>}
                            {evidenceColOrder.visibility["evidence"] !== false && (
                              <TableCell>
                                {row.hasEvidence ? (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="gap-1.5 h-7 text-xs border-border text-foreground"
                                    onClick={() => generateEvidencePdf(row)}
                                    disabled={evidencePdfLoading.has(row.jobId)}
                                  >
                                    <Camera className="h-3 w-3" />
                                    {evidencePdfLoading.has(row.jobId) ? "Zipping…" : `${totalImages} photo${totalImages !== 1 ? "s" : ""}`}
                                  </Button>
                                ) : (
                                  <span className="text-xs text-muted-foreground">—</span>
                                )}
                              </TableCell>
                            )}
                          </TableRow>
                        );
                      })}
                      {evidenceData.rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={EVIDENCE_COLUMNS.filter(c => evidenceColOrder.visibility[c.key] !== false).length} className="text-center text-muted-foreground py-8 text-sm">
                            No jobs found for the selected filters.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Camera className="mb-2 h-8 w-8" />
                <p className="text-sm">Select filters and click Generate to view evidence report.</p>
              </div>
            )}
          </TabsContent>
        )}

        {/* ─── SUPPLIER JOBS REPORT ─── */}
        {canSupplierJobs && (
          <TabsContent value="supplier-jobs" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label className="text-muted-foreground text-xs">Supplier Name</Label>
                  <Select value={supplierJobsSupplierId} onValueChange={setSupplierJobsSupplierId}>
                    <SelectTrigger className="mt-1 w-52 border-border bg-card text-foreground">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Suppliers</SelectItem>
                      {supplierList.map((s) => (
                        <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">Supplier Status</Label>
                  <Select value={supplierJobsStatus} onValueChange={setSupplierJobsStatus}>
                    <SelectTrigger className="mt-1 w-44 border-border bg-card text-foreground">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Statuses</SelectItem>
                      <SelectItem value="PENDING">Pending</SelectItem>
                      <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                      <SelectItem value="IN_PLACE">In Place</SelectItem>
                      <SelectItem value="COMPLETED">Completed</SelectItem>
                      <SelectItem value="NO_SHOW">No Show</SelectItem>
                      <SelectItem value="CANCELLED">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={supplierJobsFrom}
                    onChange={(e) => setSupplierJobsFrom(e.target.value)}
                    className="mt-1 w-44 border-border bg-card text-foreground"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={supplierJobsTo}
                    onChange={(e) => setSupplierJobsTo(e.target.value)}
                    className="mt-1 w-44 border-border bg-card text-foreground"
                  />
                </div>
                <Button onClick={fetchSupplierJobs} disabled={supplierJobsLoading} className="gap-1.5">
                  {supplierJobsLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  {t("reports.generate")}
                </Button>
                {supplierJobsData && (
                  <>
                    <Button variant="outline" onClick={exportSupplierJobsPdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> {t("reports.pdf")}
                    </Button>
                    <Button variant="outline" onClick={exportSupplierJobsExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {supplierJobsData ? (
              <>
                <div className="grid grid-cols-3 gap-1.5">
                  <StatCard label="Total Jobs" value={supplierJobsData.total} />
                  <StatCard
                    label="Completed"
                    value={supplierJobsData.rows.filter((r) => r.supplierStatus === "COMPLETED").length}
                    color="text-emerald-600 dark:text-emerald-400"
                  />
                  <StatCard
                    label="Pending"
                    value={supplierJobsData.rows.filter((r) => r.supplierStatus === "PENDING").length}
                    color="text-amber-600 dark:text-amber-400"
                  />
                </div>

                <div className="flex justify-end mb-2">
                  <ColumnVisibilityControl columns={SUPPLIER_JOBS_COLUMNS} visibility={supplierJobsColOrder.visibility} onSave={supplierJobsColOrder.saveVisibility} />
                </div>
                <div ref={supplierJobsPrintRef}>
                  <div className="rounded-md border border-border overflow-x-auto [overflow-y:clip]">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border bg-muted">
                          {supplierJobsColOrder.visibility["jobRef"] !== false && <SortableHeader label="Job Ref" sortKey="jobRef" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                          {supplierJobsColOrder.visibility["agentName"] !== false && <SortableHeader label="Agent Name" sortKey="agentName" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                          {supplierJobsColOrder.visibility["agentRef"] !== false && <SortableHeader label="Agent Ref" sortKey="agentRef" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                          {supplierJobsColOrder.visibility["serviceDate"] !== false && <SortableHeader label="Service Date" sortKey="serviceDate" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                          {supplierJobsColOrder.visibility["route"] !== false && <SortableHeader label="Route" sortKey="route" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                          {supplierJobsColOrder.visibility["supplierName"] !== false && <SortableHeader label="Supplier" sortKey="supplierName" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                          {supplierJobsColOrder.visibility["supplierStatus"] !== false && <SortableHeader label="Supplier Status" sortKey="supplierStatus" currentKey={supplierJobsSort.sortKey} currentDir={supplierJobsSort.sortDir} onSort={supplierJobsSort.onSort} />}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {supplierJobsSort.sortedData.map((row) => (
                          <TableRow key={row.id} className="border-border hover:bg-muted/30">
                            {supplierJobsColOrder.visibility["jobRef"] !== false && <TableCell className="font-mono text-sm">{row.jobRef}</TableCell>}
                            {supplierJobsColOrder.visibility["agentName"] !== false && <TableCell className="text-sm text-foreground">{row.agentName}</TableCell>}
                            {supplierJobsColOrder.visibility["agentRef"] !== false && <TableCell className="text-sm text-muted-foreground">{row.agentRef}</TableCell>}
                            {supplierJobsColOrder.visibility["serviceDate"] !== false && (
                              <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                                {new Date(row.serviceDate).toLocaleDateString()}
                              </TableCell>
                            )}
                            {supplierJobsColOrder.visibility["route"] !== false && <TableCell className="text-sm text-foreground">{row.route}</TableCell>}
                            {supplierJobsColOrder.visibility["supplierName"] !== false && <TableCell className="text-sm text-foreground">{row.supplierName}</TableCell>}
                            {supplierJobsColOrder.visibility["supplierStatus"] !== false && (
                              <TableCell>
                                <StatusBadge status={row.supplierStatus} />
                              </TableCell>
                            )}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Truck className="mb-2 h-8 w-8" />
                <p className="text-sm">Select filters and click Generate to view supplier jobs.</p>
              </div>
            )}
          </TabsContent>
        )}
        {/* ─── CAR JOBS REPORT ─── */}
        {canCarJobs && (
          <TabsContent value="car-jobs" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label className="text-muted-foreground text-xs">Vehicle</Label>
                  <div className="mt-1">
                    <SearchableCombobox
                      items={[
                        { value: "ALL", label: "All Owned Cars" },
                        ...ownedVehicleList.map((v) => ({ value: v.id, label: v.plateNumber })),
                      ]}
                      value={carJobsVehicleId}
                      onChange={setCarJobsVehicleId}
                      placeholder="All Owned Cars"
                      searchPlaceholder="Search plate number…"
                      triggerClassName="w-52 border-border bg-card text-foreground"
                    />
                  </div>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={carJobsFrom}
                    onChange={(e) => setCarJobsFrom(e.target.value)}
                    className="mt-1 w-44 border-border bg-card text-foreground"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={carJobsTo}
                    onChange={(e) => setCarJobsTo(e.target.value)}
                    className="mt-1 w-44 border-border bg-card text-foreground"
                  />
                </div>
                <Button onClick={fetchCarJobs} disabled={carJobsLoading} className="gap-1.5">
                  {carJobsLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  {t("reports.generate")}
                </Button>
                {carJobsData && (
                  <>
                    <Button variant="outline" onClick={exportCarJobsPdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> {t("reports.pdf")}
                    </Button>
                    <Button variant="outline" onClick={exportCarJobsExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> {t("reports.excel")}
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {carJobsData ? (
              <>
                <div className="grid grid-cols-3 gap-1.5">
                  <StatCard label="Total Jobs" value={carJobsData.total} />
                  <StatCard
                    label="Completed"
                    value={carJobsData.rows.filter((r) => r.jobStatus === "COMPLETED").length}
                    color="text-emerald-600 dark:text-emerald-400"
                  />
                  <StatCard
                    label="Pending"
                    value={carJobsData.rows.filter((r) => r.jobStatus === "PENDING").length}
                    color="text-amber-600 dark:text-amber-400"
                  />
                </div>

                <div className="flex justify-end mb-2">
                  <ColumnVisibilityControl columns={CAR_JOBS_COLUMNS} visibility={carJobsColOrder.visibility} onSave={carJobsColOrder.saveVisibility} />
                </div>
                <div ref={carJobsPrintRef}>
                  <div className="rounded-md border border-border overflow-x-auto [overflow-y:clip]">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border bg-muted">
                          {carJobsColOrder.visibility["jobRef"] !== false && <SortableHeader label="Job Ref" sortKey="jobRef" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["agentName"] !== false && <SortableHeader label="Agent Name" sortKey="agentName" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["serviceDate"] !== false && <SortableHeader label="Service Date" sortKey="serviceDate" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["origin"] !== false && <SortableHeader label="Origin" sortKey="origin" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["destination"] !== false && <SortableHeader label="Destination" sortKey="destination" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["plateNumber"] !== false && <SortableHeader label="Vehicle" sortKey="plateNumber" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["driver"] !== false && <SortableHeader label="Driver" sortKey="driver" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["jobStatus"] !== false && <SortableHeader label="Job Status" sortKey="jobStatus" currentKey={carJobsSort.sortKey} currentDir={carJobsSort.sortDir} onSort={carJobsSort.onSort} />}
                          {carJobsColOrder.visibility["usdPrice"] !== false && <TableHead className="text-right font-semibold text-green-600 dark:text-green-400">USD Transfer Price</TableHead>}
                          {carJobsColOrder.visibility["eurPrice"] !== false && <TableHead className="text-right font-semibold text-blue-600 dark:text-blue-400">EUR Transfer Price</TableHead>}
                          {carJobsColOrder.visibility["egpPrice"] !== false && <TableHead className="text-right font-semibold text-amber-600 dark:text-amber-400">EGP Transfer Price</TableHead>}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {carJobsSort.sortedData.map((row) => (
                          <TableRow key={row.id} className="border-border hover:bg-muted/30">
                            {carJobsColOrder.visibility["jobRef"] !== false && <TableCell className="font-mono text-sm">{row.jobRef}</TableCell>}
                            {carJobsColOrder.visibility["agentName"] !== false && <TableCell className="text-sm text-foreground">{row.agentName}</TableCell>}
                            {carJobsColOrder.visibility["serviceDate"] !== false && (
                              <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                                {new Date(row.serviceDate).toLocaleDateString()}
                              </TableCell>
                            )}
                            {carJobsColOrder.visibility["origin"] !== false && <TableCell className="text-sm text-foreground">{row.origin}</TableCell>}
                            {carJobsColOrder.visibility["destination"] !== false && <TableCell className="text-sm text-foreground">{row.destination}</TableCell>}
                            {carJobsColOrder.visibility["plateNumber"] !== false && <TableCell className="font-mono text-sm text-muted-foreground">{row.plateNumber}</TableCell>}
                            {carJobsColOrder.visibility["driver"] !== false && <TableCell className="text-sm text-foreground">{row.driver}</TableCell>}
                            {carJobsColOrder.visibility["jobStatus"] !== false && (
                              <TableCell>
                                <StatusBadge status={row.jobStatus} />
                              </TableCell>
                            )}
                            {carJobsColOrder.visibility["usdPrice"] !== false && (
                              <TableCell className="text-right text-sm font-mono">
                                {row.transferPriceCurrency === "USD" && row.transferPrice !== null
                                  ? row.transferPrice.toFixed(2)
                                  : <span className="text-muted-foreground">—</span>}
                              </TableCell>
                            )}
                            {carJobsColOrder.visibility["eurPrice"] !== false && (
                              <TableCell className="text-right text-sm font-mono">
                                {row.transferPriceCurrency === "EUR" && row.transferPrice !== null
                                  ? row.transferPrice.toFixed(2)
                                  : <span className="text-muted-foreground">—</span>}
                              </TableCell>
                            )}
                            {carJobsColOrder.visibility["egpPrice"] !== false && (
                              <TableCell className="text-right text-sm font-mono">
                                {row.transferPriceCurrency === "EGP" && row.transferPrice !== null
                                  ? row.transferPrice.toFixed(2)
                                  : <span className="text-muted-foreground">—</span>}
                              </TableCell>
                            )}
                          </TableRow>
                        ))}
                        <TableRow className="border-t-2 border-border bg-muted/50 font-semibold">
                          <TableCell colSpan={
                            [
                              carJobsColOrder.visibility["jobRef"] !== false,
                              carJobsColOrder.visibility["agentName"] !== false,
                              carJobsColOrder.visibility["serviceDate"] !== false,
                              carJobsColOrder.visibility["origin"] !== false,
                              carJobsColOrder.visibility["destination"] !== false,
                              carJobsColOrder.visibility["plateNumber"] !== false,
                              carJobsColOrder.visibility["driver"] !== false,
                              carJobsColOrder.visibility["jobStatus"] !== false,
                            ].filter(Boolean).length
                          } className="text-sm text-muted-foreground">Totals</TableCell>
                          {carJobsColOrder.visibility["usdPrice"] !== false && (
                            <TableCell className="text-right text-sm font-mono font-bold text-green-600 dark:text-green-400">
                              {carJobsData.totals.USD > 0 ? `USD ${carJobsData.totals.USD.toFixed(2)}` : "—"}
                            </TableCell>
                          )}
                          {carJobsColOrder.visibility["eurPrice"] !== false && (
                            <TableCell className="text-right text-sm font-mono font-bold text-blue-600 dark:text-blue-400">
                              {carJobsData.totals.EUR > 0 ? `EUR ${carJobsData.totals.EUR.toFixed(2)}` : "—"}
                            </TableCell>
                          )}
                          {carJobsColOrder.visibility["egpPrice"] !== false && (
                            <TableCell className="text-right text-sm font-mono font-bold text-amber-600 dark:text-amber-400">
                              {carJobsData.totals.EGP > 0 ? `EGP ${carJobsData.totals.EGP.toFixed(2)}` : "—"}
                            </TableCell>
                          )}
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Car className="mb-2 h-8 w-8" />
                <p className="text-sm">Select filters and click Generate to view car jobs.</p>
              </div>
            )}
          </TabsContent>
        )}

        {/* ─── VISA REPORT ─── */}
        {canVisa && (
          <TabsContent value="visa" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex items-end gap-3 flex-wrap">
                <div>
                  <Label className="text-muted-foreground text-xs">From</Label>
                  <Input type="date" value={visaFrom} onChange={(e) => setVisaFrom(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">To</Label>
                  <Input type="date" value={visaTo} onChange={(e) => setVisaTo(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <Button onClick={fetchVisa} disabled={visaLoading} className="gap-1.5">
                  {visaLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  Generate
                </Button>
                {visaData && (
                  <>
                    <Button variant="outline" onClick={exportVisaExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> Excel
                    </Button>
                    <Button variant="outline" onClick={exportVisaPdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> PDF
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {visaData && (
              <>
                <div className="grid grid-cols-4 gap-1.5">
                  <StatCard label="Total Records" value={visaData.count} />
                  <StatCard label="Period" value={`${visaData.from} → ${visaData.to}`} />
                </div>

                <div className="overflow-x-auto rounded-md border border-border" ref={visaPrintRef}>
                  <Table>
                    <DraggableTableHeader
                      columns={VISA_COLUMNS}
                      columnOrder={visaColOrder.columns}
                      onReorder={visaColOrder.reorder}
                      visibility={visaColOrder.visibility}
                    />
                    <TableBody>
                      {visaSort.sortedData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={VISA_COLUMNS.length} className="py-8 text-center text-muted-foreground text-sm">
                            No records found
                          </TableCell>
                        </TableRow>
                      ) : (
                        visaSort.sortedData.map((row, idx) => (
                          <TableRow key={idx} className="border-border hover:bg-muted/30">
                            {visaColOrder.columns.filter((col) => visaColOrder.visibility[col] !== false).map((col) => {
                              switch (col) {
                                case "clientName": return <TableCell key={col} className="text-sm">{row.clientName}</TableCell>;
                                case "flightNo": return <TableCell key={col} className="text-xs font-mono">{row.flightNo}</TableCell>;
                                case "arrivalTime": return <TableCell key={col} className="text-xs font-mono">{row.arrivalTime ? new Date(row.arrivalTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "—"}</TableCell>;
                                case "terminal": return <TableCell key={col} className="text-xs">{row.terminal}</TableCell>;
                                default: return null;
                              }
                            })}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                <ColumnVisibilityControl columns={VISA_COLUMNS} visibility={visaColOrder.visibility} onSave={visaColOrder.saveVisibility} />
              </>
            )}
          </TabsContent>
        )}

        {/* ─── SALES REPORT ─── */}
        {canSales && (
          <TabsContent value="sales" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex items-end gap-3 flex-wrap">
                <div>
                  <Label className="text-muted-foreground text-xs">From</Label>
                  <Input type="date" value={salesFrom} onChange={(e) => setSalesFrom(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">To</Label>
                  <Input type="date" value={salesTo} onChange={(e) => setSalesTo(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <Button onClick={fetchSales} disabled={salesLoading} className="gap-1.5">
                  {salesLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  Generate
                </Button>
                {salesData && (
                  <>
                    <Button variant="outline" onClick={exportSalesExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> Excel
                    </Button>
                    <Button variant="outline" onClick={exportSalesPdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> PDF
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {salesData && (
              <>
                <div className="grid grid-cols-4 gap-1.5">
                  <StatCard label="Total Records" value={salesData.count} />
                  <StatCard label="Period" value={`${salesData.from} → ${salesData.to}`} />
                </div>

                <div className="overflow-x-auto rounded-md border border-border" ref={salesPrintRef}>
                  <Table>
                    <DraggableTableHeader
                      columns={SALES_COLUMNS}
                      columnOrder={salesColOrder.columns}
                      onReorder={salesColOrder.reorder}
                      visibility={salesColOrder.visibility}
                    />
                    <TableBody>
                      {salesSort.sortedData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={SALES_COLUMNS.length} className="py-8 text-center text-muted-foreground text-sm">
                            No records found
                          </TableCell>
                        </TableRow>
                      ) : (
                        salesSort.sortedData.map((row, idx) => (
                          <TableRow key={idx} className="border-border hover:bg-muted/30">
                            {salesColOrder.columns.filter((col) => salesColOrder.visibility[col] !== false).map((col) => {
                              switch (col) {
                                case "internalRef": return <TableCell key={col} className="text-xs font-mono">{row.internalRef}</TableCell>;
                                case "agentRef": return <TableCell key={col} className="text-xs">{row.agentRef}</TableCell>;
                                case "flightNo": return <TableCell key={col} className="text-xs font-mono">{row.flightNo}</TableCell>;
                                case "terminal": return <TableCell key={col} className="text-xs">{row.terminal}</TableCell>;
                                case "arrivalTime": return <TableCell key={col} className="text-xs font-mono">{row.arrivalTime ? new Date(row.arrivalTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "—"}</TableCell>;
                                case "pax": return <TableCell key={col} className="text-xs text-right">{row.pax}</TableCell>;
                                case "hotelName": return <TableCell key={col} className="text-sm">{row.hotelName}</TableCell>;
                                case "clientName": return <TableCell key={col} className="text-sm">{row.clientName}</TableCell>;
                                case "clientNumber": return <TableCell key={col} className="text-xs font-mono">{row.clientNumber}</TableCell>;
                                default: return null;
                              }
                            })}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                <ColumnVisibilityControl columns={SALES_COLUMNS} visibility={salesColOrder.visibility} onSave={salesColOrder.saveVisibility} />
              </>
            )}
          </TabsContent>
        )}

        {/* ─── DEPARTURE REPORT ─── */}
        {canDeparture && (
          <TabsContent value="departure" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex items-end gap-3 flex-wrap">
                <div>
                  <Label className="text-muted-foreground text-xs">From</Label>
                  <Input type="date" value={departureFrom} onChange={(e) => setDepartureFrom(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">To</Label>
                  <Input type="date" value={departureTo} onChange={(e) => setDepartureTo(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">Service Type</Label>
                  <Select value={departureServiceType} onValueChange={setDepartureServiceType}>
                    <SelectTrigger className="mt-1 w-36 border-border bg-card text-foreground">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Types</SelectItem>
                      {SERVICE_TYPE_DROPDOWN_OPTIONS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={fetchDeparture} disabled={departureLoading} className="gap-1.5">
                  {departureLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  Generate
                </Button>
                {departureData && (
                  <>
                    <Button variant="outline" onClick={exportDeparturePdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> PDF
                    </Button>
                    <Button variant="outline" onClick={exportDepartureExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> Excel
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {departureData && (
              <>
                <div className="grid grid-cols-4 gap-1.5">
                  <StatCard label="Total Records" value={departureData.count} />
                  <StatCard label="Period" value={`${departureData.from} → ${departureData.to}`} />
                </div>

                <div className="overflow-x-auto rounded-md border border-border" ref={departurePrintRef}>
                  <Table>
                    <DraggableTableHeader
                      columns={DEPARTURE_COLUMNS}
                      columnOrder={departureColOrder.columns}
                      onReorder={departureColOrder.reorder}
                      visibility={departureColOrder.visibility}
                    />
                    <TableBody>
                      {departureSort.sortedData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={DEPARTURE_COLUMNS.length} className="py-8 text-center text-muted-foreground text-sm">
                            No records found
                          </TableCell>
                        </TableRow>
                      ) : (
                        departureSort.sortedData.map((row, idx) => (
                          <TableRow key={idx} className="border-border hover:bg-muted/30">
                            {departureColOrder.columns.filter((col) => departureColOrder.visibility[col] !== false).map((col) => {
                              switch (col) {
                                case "serviceDate": return <TableCell key={col} className="text-xs font-mono">{row.serviceDate ? new Date(row.serviceDate).toLocaleDateString(locale) : "—"}</TableCell>;
                                case "customerName": return <TableCell key={col} className="text-sm">{row.customerName}</TableCell>;
                                case "customerNumber": return <TableCell key={col} className="text-xs font-mono">{row.customerNumber}</TableCell>;
                                case "pax": return <TableCell key={col} className="text-xs text-right">{row.pax}</TableCell>;
                                case "pickupTime": return <TableCell key={col} className="text-xs font-mono">{row.pickupTime ? new Date(row.pickupTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "—"}</TableCell>;
                                case "serviceType": return <TableCell key={col}><Badge variant="outline" className="text-xs">{serviceTypeLabel(row.serviceType)}</Badge></TableCell>;
                                default: return null;
                              }
                            })}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                <ColumnVisibilityControl columns={DEPARTURE_COLUMNS} visibility={departureColOrder.visibility} onSave={departureColOrder.saveVisibility} />
              </>
            )}
          </TabsContent>
        )}

        {/* ─── FLIGHT DELAY REPORT ─── */}
        {canFlightDelay && (
          <TabsContent value="flight-delay" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex items-end gap-3 flex-wrap">
                <div>
                  <Label className="text-muted-foreground text-xs">From</Label>
                  <Input type="date" value={flightDelayFrom} onChange={(e) => setFlightDelayFrom(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">To</Label>
                  <Input type="date" value={flightDelayTo} onChange={(e) => setFlightDelayTo(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">Rep Name</Label>
                  <Select value={flightDelayRepName} onValueChange={setFlightDelayRepName}>
                    <SelectTrigger className="mt-1 w-48 border-border bg-card text-foreground">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Reps</SelectItem>
                      {repList.map((r) => (
                        <SelectItem key={r.id} value={r.name}>{r.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={fetchFlightDelay} disabled={flightDelayLoading} className="gap-1.5">
                  {flightDelayLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  Generate
                </Button>
                {flightDelayData && (
                  <>
                    <Button variant="outline" onClick={exportFlightDelayPdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> PDF
                    </Button>
                    <Button variant="outline" onClick={exportFlightDelayExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> Excel
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {flightDelayData && (
              <>
                <div className="grid grid-cols-4 gap-1.5">
                  <StatCard label="Total Delays" value={flightDelayData.count} />
                  <StatCard label="Period" value={`${flightDelayData.from} → ${flightDelayData.to}`} />
                </div>

                <div className="overflow-x-auto rounded-md border border-border" ref={flightDelayPrintRef}>
                  <Table>
                    <DraggableTableHeader
                      columns={FLIGHT_DELAY_COLUMNS}
                      columnOrder={flightDelayColOrder.columns}
                      onReorder={flightDelayColOrder.reorder}
                      visibility={flightDelayColOrder.visibility}
                    />
                    <TableBody>
                      {flightDelaySort.sortedData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={FLIGHT_DELAY_COLUMNS.length} className="py-8 text-center text-muted-foreground text-sm">
                            No flight delays found
                          </TableCell>
                        </TableRow>
                      ) : (
                        flightDelaySort.sortedData.map((row, idx) => (
                          <TableRow key={idx} className="border-border hover:bg-muted/30">
                            {flightDelayColOrder.columns.filter((col) => flightDelayColOrder.visibility[col] !== false).map((col) => {
                              switch (col) {
                                case "internalRef": return <TableCell key={col} className="text-xs font-mono font-semibold">{row.internalRef}</TableCell>;
                                case "agentRef": return <TableCell key={col} className="text-xs font-mono">{row.agentRef ?? "—"}</TableCell>;
                                case "jobDate": return <TableCell key={col} className="text-xs">{row.jobDate ? new Date(row.jobDate).toLocaleDateString(locale) : "—"}</TableCell>;
                                case "oldArrivalDate": return <TableCell key={col} className="text-xs">{row.oldArrivalDate ? new Date(row.oldArrivalDate).toLocaleDateString(locale) : "—"}</TableCell>;
                                case "oldArrivalTime": return <TableCell key={col} className="text-xs font-mono">{row.oldArrivalTime ?? "—"}</TableCell>;
                                case "newArrivalDate": return <TableCell key={col} className="text-xs text-amber-600 dark:text-amber-400">{new Date(row.newArrivalDate).toLocaleDateString(locale)}</TableCell>;
                                case "newArrivalTime": return <TableCell key={col} className="text-xs font-mono text-amber-600 dark:text-amber-400">{row.newArrivalTime}</TableCell>;
                                case "reportedBy": return <TableCell key={col} className="text-sm">{row.reportedBy}</TableCell>;
                                case "currentRepName": return (
                                  <TableCell key={col} className="text-sm">
                                    {row.currentRepName ? (
                                      <span className="text-blue-600 dark:text-blue-400">{row.currentRepName}</span>
                                    ) : "—"}
                                  </TableCell>
                                );
                                default: return null;
                              }
                            })}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                <ColumnVisibilityControl columns={FLIGHT_DELAY_COLUMNS} visibility={flightDelayColOrder.visibility} onSave={flightDelayColOrder.saveVisibility} />
              </>
            )}
          </TabsContent>
        )}

        {/* ─── REVIEW REPORT ─── */}
        {canReview && (
          <TabsContent value="review" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex items-end gap-3 flex-wrap">
                <div>
                  <Label className="text-muted-foreground text-xs">From</Label>
                  <Input type="date" value={reviewFrom} onChange={(e) => setReviewFrom(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">To</Label>
                  <Input type="date" value={reviewTo} onChange={(e) => setReviewTo(e.target.value)} className="mt-1 w-44 border-border bg-card text-foreground" />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">Job Status</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="mt-1 w-48 justify-between border-border bg-card text-foreground font-normal">
                        <span className="truncate">
                          {reviewStatus.length === 0
                            ? "All Statuses"
                            : reviewStatus.map((s) => s.replace(/_/g, " ")).join(", ")}
                        </span>
                        <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-48 p-2" align="start">
                      {(["PENDING","ASSIGNED","IN_PROGRESS","IN_PLACE","COMPLETED","CANCELLED","NO_SHOW"] as const).map((s) => (
                        <label key={s} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent">
                          <Checkbox
                            checked={reviewStatus.includes(s)}
                            onCheckedChange={(checked) =>
                              setReviewStatus((prev) =>
                                checked ? [...prev, s] : prev.filter((x) => x !== s)
                              )
                            }
                          />
                          {s.replace(/_/g, " ")}
                        </label>
                      ))}
                      {reviewStatus.length > 0 && (
                        <Button variant="ghost" size="sm" className="mt-1 w-full text-xs" onClick={() => setReviewStatus([])}>
                          Clear
                        </Button>
                      )}
                    </PopoverContent>
                  </Popover>
                </div>
                <Button onClick={fetchReview} disabled={reviewLoading} className="gap-1.5">
                  {reviewLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  Generate
                </Button>
                {reviewData && (
                  <>
                    <Button variant="outline" onClick={exportReviewExcel} className="gap-1.5 border-border text-foreground">
                      <FileSpreadsheet className="h-4 w-4" /> Excel
                    </Button>
                    <Button variant="outline" onClick={exportReviewPdf} className="gap-1.5 border-border text-foreground">
                      <Printer className="h-4 w-4" /> PDF
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {reviewData && (
              <>
                <div className="grid grid-cols-4 gap-1.5">
                  <StatCard label="Total Records" value={reviewData.count} />
                  <StatCard label="Period" value={`${reviewData.from} → ${reviewData.to}`} />
                </div>

                <div className="overflow-x-auto rounded-md border border-border" ref={reviewPrintRef}>
                  <Table>
                    <DraggableTableHeader
                      columns={REVIEW_COLUMNS}
                      columnOrder={reviewColOrder.columns}
                      onReorder={reviewColOrder.reorder}
                      visibility={reviewColOrder.visibility}
                    />
                    <TableBody>
                      {reviewSort.sortedData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={REVIEW_COLUMNS.length} className="py-8 text-center text-muted-foreground text-sm">
                            No records found
                          </TableCell>
                        </TableRow>
                      ) : (
                        reviewSort.sortedData.map((row, idx) => (
                          <TableRow key={idx} className="border-border hover:bg-muted/30">
                            {reviewColOrder.columns.filter((col) => reviewColOrder.visibility[col] !== false).map((col) => {
                              switch (col) {
                                case "internalRef": return <TableCell key={col} className="text-xs font-mono">{row.internalRef}</TableCell>;
                                case "agentName": return <TableCell key={col} className="text-xs">{row.agentName}</TableCell>;
                                case "agentRef": return <TableCell key={col} className="text-xs font-mono">{row.agentRef}</TableCell>;
                                case "serviceDate": return <TableCell key={col} className="text-xs">{row.serviceDate ? new Date(row.serviceDate).toLocaleDateString(locale) : "—"}</TableCell>;
                                case "serviceType": return <TableCell key={col} className="text-xs"><Badge variant="secondary">{serviceTypeLabel(row.serviceType)}</Badge></TableCell>;
                                case "status": return <TableCell key={col} className="text-xs"><Badge variant="outline">{row.status}</Badge></TableCell>;
                                case "pax": return <TableCell key={col} className="text-xs text-right">{row.pax}</TableCell>;
                                case "clientName": return <TableCell key={col} className="text-xs">{row.clientName}</TableCell>;
                                case "origin": return <TableCell key={col} className="text-xs">{row.origin}</TableCell>;
                                case "destination": return <TableCell key={col} className="text-xs">{row.destination}</TableCell>;
                                case "transferPrice": return <TableCell key={col} className="text-xs text-right text-sky-500">{row.transferPrice != null ? row.transferPrice.toLocaleString() : "—"}</TableCell>;
                                case "transferPriceCurrency": return <TableCell key={col} className="text-xs text-sky-500">{row.transferPrice != null ? row.transferPriceCurrency : "—"}</TableCell>;
                                case "driverName": return <TableCell key={col} className="text-xs">{row.driverName}</TableCell>;
                                case "repName": return <TableCell key={col} className="text-xs">{row.repName}</TableCell>;
                                case "notes": return <TableCell key={col} className="text-xs text-muted-foreground max-w-48 truncate">{row.notes || "—"}</TableCell>;
                                default: return null;
                              }
                            })}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                <ColumnVisibilityControl columns={REVIEW_COLUMNS} visibility={reviewColOrder.visibility} onSave={reviewColOrder.saveVisibility} />
              </>
            )}
          </TabsContent>
        )}

        {canGuestSurveys && (
          <TabsContent value="guest-surveys" className="space-y-4">
            <Card className="border-border bg-card p-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={guestSurveyFrom}
                    onChange={(e) => setGuestSurveyFrom(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm w-36"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={guestSurveyTo}
                    onChange={(e) => setGuestSurveyTo(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm w-36"
                  />
                </div>
                <div className="min-w-[180px]">
                  <Label className="text-muted-foreground text-xs">Rep Name</Label>
                  <Select value={guestSurveyRepId} onValueChange={setGuestSurveyRepId}>
                    <SelectTrigger className="border-border bg-muted/50 mt-0.5 h-8 text-sm">
                      <SelectValue placeholder="All Reps" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Reps</SelectItem>
                      {repList.map((r) => (
                        <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" onClick={fetchGuestSurveys} disabled={guestSurveyLoading} className="gap-1.5">
                  {guestSurveyLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                  {t("common.search")}
                </Button>
                {guestSurveyData && guestSurveyData.rows.length > 0 && (
                  <>
                    <Button size="sm" variant="outline" onClick={exportGuestSurveysPdf} className="gap-1.5 ml-auto">
                      <Printer className="h-3.5 w-3.5" />
                      {t("reports.exportPdf")}
                    </Button>
                    <Button size="sm" variant="outline" onClick={exportGuestSurveysExcel} className="gap-1.5">
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      {t("reports.excel")}
                    </Button>
                  </>
                )}
              </div>
            </Card>

            {guestSurveyLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : guestSurveyData ? (
              <Card className="border-border bg-card p-4">
                <div ref={guestSurveyPrintRef}>
                  <div className="mb-4 flex flex-wrap gap-4">
                    <div className="rounded-lg border border-border bg-muted/20 px-4 py-2">
                      <p className="text-xs text-muted-foreground">Total Surveys</p>
                      <p className="text-lg font-bold text-foreground">{guestSurveyData.count}</p>
                    </div>
                    <div className="rounded-lg border border-border bg-muted/20 px-4 py-2">
                      <p className="text-xs text-muted-foreground">Reps</p>
                      <p className="text-lg font-bold text-foreground">{guestSurveyData.reps.length}</p>
                    </div>
                  </div>

                  {guestSurveyData.reps.length > 0 && (
                    <div className="mb-4 flex flex-wrap gap-2">
                      {guestSurveyData.reps.map((r) => (
                        <span key={r.repId} className="rounded-full border border-border bg-muted/30 px-3 py-1 text-xs text-foreground">
                          {r.repName}: <b>{r.count}</b>
                        </span>
                      ))}
                    </div>
                  )}

                  {guestSurveyData.rows.length === 0 ? (
                    <p className="py-8 text-center text-sm text-muted-foreground">No surveys found for this period.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow className="border-border">
                            <TableHead className="text-muted-foreground text-xs">Date</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Rep</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Job Ref</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Flight</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Hotel</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Nationality</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Age</TableHead>
                            <TableHead className="text-muted-foreground text-xs text-center">Adt</TableHead>
                            <TableHead className="text-muted-foreground text-xs text-center">Chd</TableHead>
                            <TableHead className="text-muted-foreground text-xs text-center">Inf</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Stay</TableHead>
                            <TableHead className="text-muted-foreground text-xs text-center">Repeat</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Local Agent</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Contact</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Email</TableHead>
                            <TableHead className="text-muted-foreground text-xs">Comment</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {guestSurveyData.rows.map((row, idx) => (
                            <TableRow
                              key={row.id}
                              className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                            >
                              <TableCell className="text-xs whitespace-nowrap">{formatDate(row.jobDate)}</TableCell>
                              <TableCell className="text-xs font-medium whitespace-nowrap">{row.repName}</TableCell>
                              <TableCell className="text-xs font-mono whitespace-nowrap">{row.internalRef}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.flightNo}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.hotelName}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.guestNationality}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.ageRange}</TableCell>
                              <TableCell className="text-xs text-center">{row.noOfAdults}</TableCell>
                              <TableCell className="text-xs text-center">{row.noOfChildren}</TableCell>
                              <TableCell className="text-xs text-center">{row.noOfInfants}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.stayLength || "—"}</TableCell>
                              <TableCell className="text-xs text-center">{row.repeaterGuest}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.localTravelAgent || "—"}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.contactNumber}</TableCell>
                              <TableCell className="text-xs whitespace-nowrap">{row.email || "—"}</TableCell>
                              <TableCell className="text-xs max-w-[240px] truncate" title={row.generalComment}>{row.generalComment}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </div>
              </Card>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">Select a date range and search to view guest surveys.</p>
            )}
          </TabsContent>
        )}

      </Tabs>

      {/* ─── REP FEE DETAIL MODAL ─── */}
      <Dialog
        open={repModalOpen}
        onOpenChange={(open) => {
          setRepModalOpen(open);
          if (!open && selectedRep) {
            // Persist the computed net total back to the list row
            const net = computeRepNet(selectedRep.fees);
            setRepNetTotals((prev) => ({ ...prev, [selectedRep.repId]: net }));
            setSelectedRep(null);
          }
        }}
      >
        <DialogContent className="max-h-[85vh] overflow-y-auto border-border bg-popover text-foreground sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle className="text-foreground">
              {selectedRep?.repName} &mdash; {repFeeFrom === repFeeTo ? repFeeFrom : `${repFeeFrom} → ${repFeeTo}`}
            </DialogTitle>
          </DialogHeader>

          {selectedRep && (
            <div className="space-y-4 py-2">
              {groupByFlight(selectedRep.fees).map((group) => (
                <div key={`${group.flightNo}|${group.carrier}`}>
                  <div className="flex items-center gap-2 mb-2 px-1">
                    <Badge
                      variant="outline"
                      className="bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20 font-mono"
                    >
                      {group.flightNo}
                    </Badge>
                    {group.carrier && (
                      <span className="text-xs text-muted-foreground">
                        {group.carrier}
                      </span>
                    )}
                  </div>
                  <div className="overflow-x-auto [overflow-y:clip]">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border bg-muted">
                        <TableHead className="w-8 px-1" />
                        <TableHead className="text-muted-foreground text-xs">{t("reports.jobRef")}</TableHead>
                        <TableHead className="text-muted-foreground text-xs">{t("jobs.type")}</TableHead>
                        <TableHead className="text-muted-foreground text-xs text-right">
                          {t("dispatch.pax")}
                        </TableHead>
                        <TableHead className="text-muted-foreground text-xs">Route</TableHead>
                        <TableHead className="text-muted-foreground text-xs">Arr. Flight</TableHead>
                        <TableHead className="text-muted-foreground text-xs">Dep. Pickup</TableHead>
                        <TableHead className="text-muted-foreground text-xs">{t("locations.hotel")}</TableHead>
                        <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>
                        <TableHead className="text-muted-foreground text-xs text-center">Missed</TableHead>
                        <TableHead className="text-muted-foreground text-xs text-center">Att<br/><span className="text-[10px] font-normal opacity-75">20pt</span></TableHead>
                        <TableHead className="text-muted-foreground text-xs text-center">App<br/><span className="text-[10px] font-normal opacity-75">15pt</span></TableHead>
                        <TableHead className="text-muted-foreground text-xs text-center">Work<br/><span className="text-[10px] font-normal opacity-75">15pt</span></TableHead>
                        <TableHead className="text-muted-foreground text-xs text-center">Survey<br/><span className="text-[10px] font-normal opacity-75">15pt</span></TableHead>
                        <TableHead className="text-muted-foreground text-xs text-center">Rev<br/><span className="text-[10px] font-normal opacity-75">35pt</span></TableHead>
                        <TableHead className="text-muted-foreground text-xs text-right">Score</TableHead>
                        <TableHead className="text-muted-foreground text-xs text-right">Fee</TableHead>
                        <TableHead className="text-muted-foreground text-xs text-right">Deductions</TableHead>
                        <TableHead className="text-muted-foreground text-xs">Eval</TableHead>
                        <TableHead className="text-muted-foreground text-xs">Photos</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {group.jobs.map((fee, idx) => {
                        const jobId = fee.trafficJob.id;
                        const isArr = fee.trafficJob.serviceType === "ARR";
                        const hasInPlace = fee.inPlaceEvidence.length > 0;
                        const isCompleted = fee.repStatus === "COMPLETED" || fee.trafficJob.status === "COMPLETED";
                        const currentScore = scoreEdits[jobId] ?? fee.repJobScore;
                        // Survey point can be toggled once a survey exists for the job
                        // (submitting one auto-sets it; this lets the accountant adjust).
                        const hasSurvey = fee.hasSurvey || (currentScore?.survey ?? false);
                        const isSaving = scoreSaving[jobId] ?? false;
                        const isMissed = missedJobs[jobId] ?? false;

                        const toggleScore = (field: "attendance" | "appearance" | "work" | "survey" | "review", enabled: boolean) => {
                          if (!enabled || isMissed) return;
                          const base = currentScore ?? { attendance: false, appearance: false, work: false, survey: false, review: false, total: null, fee: null, evaluation: null };
                          const next = { attendance: base.attendance, appearance: base.appearance, work: base.work, survey: base.survey, review: base.review, [field]: !base[field] };
                          saveRepScore(jobId, next);
                        };

                        const evalColor =
                          currentScore?.evaluation === "Excellent" ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" :
                          currentScore?.evaluation === "Good" ? "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20" :
                          currentScore?.evaluation === "Average" ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20" :
                          currentScore?.evaluation === "Poor" ? "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20" : "";

                        return (
                          <TableRow
                            key={fee.id}
                            className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                          >
                            <TableCell className="w-8 px-1">
                              <button
                                type="button"
                                onClick={() => setJobDetailId(fee.trafficJob.id)}
                                className="flex h-6 w-6 items-center justify-center rounded hover:bg-muted/50 transition-colors"
                                title="View job details"
                              >
                                <Eye className="h-3.5 w-3.5 text-muted-foreground/60 hover:text-foreground transition-colors" />
                              </button>
                            </TableCell>
                            <TableCell className="text-foreground font-mono text-xs">
                              {fee.trafficJob.internalRef}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant="outline"
                                className={
                                  isArr
                                    ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                                    : "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 border-zinc-500/20"
                                }
                              >
                                {serviceTypeLabel(fee.trafficJob.serviceType)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right text-muted-foreground">
                              {fee.trafficJob.paxCount}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                              {(fee.trafficJob.originAirport?.code || fee.trafficJob.fromZone?.name || fee.trafficJob.originZone?.name || fee.trafficJob.originHotel?.name || "\u2014")}{" \u2192 "}{(fee.trafficJob.destinationAirport?.code || fee.trafficJob.toZone?.name || fee.trafficJob.destinationZone?.name || fee.trafficJob.destinationHotel?.name || "\u2014")}
                            </TableCell>
                            <TableCell className="text-xs font-mono text-muted-foreground">
                              {fee.trafficJob.flight?.arrivalTime ? new Date(fee.trafficJob.flight.arrivalTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "\u2014"}
                            </TableCell>
                            <TableCell className="text-xs font-mono text-muted-foreground">
                              {fee.trafficJob.pickUpTime ? new Date(fee.trafficJob.pickUpTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit" }) : "\u2014"}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {fee.trafficJob.hotel?.name || "\u2014"}
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-col gap-1">
                                <StatusBadge status={fee.status} />
                                {fee.isPosted && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/20 px-2 py-0.5 text-[10px] font-medium text-sky-600 dark:text-sky-400">
                                    ✓ Posted
                                  </span>
                                )}
                              </div>
                            </TableCell>
                            {/* Missed — disables all score checkboxes */}
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                checked={isMissed}
                                onChange={() => setMissedJobs((prev) => ({ ...prev, [jobId]: !isMissed }))}
                                title="Mark as missed"
                                className="h-4 w-4 cursor-pointer accent-red-600"
                              />
                            </TableCell>
                            {/* Attendance — requires inPlaceEvidence */}
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                disabled={!hasInPlace || isSaving || isMissed}
                                checked={!isMissed && (currentScore?.attendance ?? false)}
                                onChange={() => toggleScore("attendance", hasInPlace)}
                                title={hasInPlace ? "Attendance (20pt)" : "Requires In Place evidence"}
                                className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                              />
                            </TableCell>
                            {/* Appearance — requires inPlaceEvidence */}
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                disabled={!hasInPlace || isSaving || isMissed}
                                checked={!isMissed && (currentScore?.appearance ?? false)}
                                onChange={() => toggleScore("appearance", hasInPlace)}
                                title={hasInPlace ? "Appearance (15pt)" : "Requires In Place evidence"}
                                className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                              />
                            </TableCell>
                            {/* Work — always enabled */}
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                disabled={isSaving || isMissed}
                                checked={!isMissed && (currentScore?.work ?? false)}
                                onChange={() => toggleScore("work", true)}
                                title="Work (15pt)"
                                className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                              />
                            </TableCell>
                            {/* Survey — enabled once a guest survey exists for the job */}
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                disabled={!hasSurvey || isSaving || isMissed}
                                checked={!isMissed && (currentScore?.survey ?? false)}
                                onChange={() => toggleScore("survey", hasSurvey)}
                                title={hasSurvey ? "Survey (15pt)" : "Requires a submitted guest survey"}
                                className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                              />
                            </TableCell>
                            {/* Review — always enabled */}
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                disabled={isSaving || isMissed}
                                checked={!isMissed && (currentScore?.review ?? false)}
                                onChange={() => toggleScore("review", true)}
                                title="Review (35pt)"
                                className="h-4 w-4 cursor-pointer accent-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed"
                              />
                            </TableCell>
                            <TableCell className="text-right font-mono text-sm font-semibold">
                              {isMissed ? (
                                <span className="text-muted-foreground">—</span>
                              ) : isSaving ? (
                                <Loader2 className="h-3 w-3 animate-spin inline" />
                              ) : currentScore?.total !== undefined && currentScore.total !== null ? (
                                <span>{currentScore.total}</span>
                              ) : "\u2014"}
                            </TableCell>
                            <TableCell className="text-right font-mono font-medium text-sm">
                              {isMissed ? (
                                <span className="text-muted-foreground">—</span>
                              ) : currentScore?.fee !== undefined && currentScore.fee !== null
                                ? `${currentScore.fee} EGP`
                                : "\u2014"}
                            </TableCell>
                            {/* Deductions — negative amount deducted from rep */}
                            <TableCell className="text-right">
                              <input
                                type="number"
                                value={deductions[jobId] ?? ""}
                                onChange={(e) => setDeductions((prev) => ({ ...prev, [jobId]: Number(e.target.value) }))}
                                placeholder="0"
                                className="w-20 text-right text-sm bg-transparent border border-border rounded px-1 py-0.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                              />
                            </TableCell>
                            <TableCell>
                              {!isMissed && currentScore?.evaluation ? (
                                <Badge variant="outline" className={evalColor}>
                                  {currentScore.evaluation}
                                </Badge>
                              ) : "\u2014"}
                            </TableCell>
                            <TableCell>
                              {hasInPlace && fee.inPlaceEvidence.flatMap(e => e.imageUrls).length > 0 ? (
                                <button
                                  type="button"
                                  onClick={() => openEvidenceView(fee.inPlaceEvidence.flatMap(e => e.imageUrls), fee.trafficJob.internalRef)}
                                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                                >
                                  <Camera className="h-3.5 w-3.5" />
                                  Display
                                </button>
                              ) : (
                                <span className="text-muted-foreground text-xs">\u2014</span>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                  </div>
                </div>
              ))}

              {(() => {
                const flightCount = groupByFlight(selectedRep.fees).length;
                const jobCount = selectedRep.fees.length;
                const computedFees = selectedRep.fees.reduce((sum, fee) => {
                  const jobId = fee.trafficJob.id;
                  if (missedJobs[jobId]) return sum;
                  const score = scoreEdits[jobId] ?? fee.repJobScore;
                  const feeAmt = fee.trafficJob.serviceType === "ARR"
                    ? (score?.fee ?? fee.amount)
                    : fee.amount;
                  return sum + (Number(feeAmt) || 0);
                }, 0);
                // Sum deductions for every job in the rep's fee list — deductions are
                // untied from the Missed flag, so they apply whether or not a job is missed.
                const relevantJobIds = new Set(selectedRep.fees.map((f) => f.trafficJob.id));
                const totalDeductions = Object.entries(deductions)
                  .filter(([k]) => relevantJobIds.has(k))
                  .reduce((s, [, v]) => s + (Number(v) || 0), 0);
                const netTotal = computedFees - totalDeductions;
                return (
                  <div className="flex justify-between items-center border-t border-border pt-3 px-1">
                    <span className="text-sm font-semibold text-foreground">
                      {t("common.total")} ({flightCount} {t("reports.flightsCount")}, {jobCount} {t("reports.jobs")})
                    </span>
                    <div className="text-right">
                      {totalDeductions !== 0 && (
                        <div className={`text-xs font-mono ${totalDeductions > 0 ? "text-red-500" : "text-emerald-500"}`}>
                          {totalDeductions > 0
                            ? `- ${fmt(totalDeductions, locale)} EGP deductions`
                            : `+ ${fmt(Math.abs(totalDeductions), locale)} EGP adjustment`}
                        </div>
                      )}
                      <span className="text-base font-medium text-emerald-600 dark:text-emerald-400 font-mono">
                        {fmt(netTotal, locale)} EGP
                      </span>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ─── EVIDENCE IMAGE VIEWER ─── */}
      <Dialog
        open={evidenceViewOpen}
        onOpenChange={(open) => {
          setEvidenceViewOpen(open);
          if (!open) {
            evidenceViewUrls.forEach((u) => { if (u.startsWith("blob:")) URL.revokeObjectURL(u); });
            setEvidenceViewUrls([]);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto border-border bg-popover text-foreground sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-foreground">
              Evidence Photos — {evidenceViewJobRef}
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            {evidenceViewLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : evidenceViewUrls.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-8">No images available.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {evidenceViewUrls.map((url, i) => (
                  <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                    <img
                      src={url}
                      alt={`Evidence ${i + 1}`}
                      className="w-full rounded-md border border-border object-cover aspect-video hover:opacity-80 transition-opacity"
                    />
                  </a>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* ─── DRIVER TRIP DETAIL MODAL ─── */}
      <Dialog
        open={driverModalOpen}
        onOpenChange={(open) => {
          setDriverModalOpen(open);
          if (!open) {
            setSelectedDriver(null);
            setDriverMissedJobs({});
            setDriverDeductions({});
          }
        }}
      >
        <DialogContent className="max-h-[85vh] overflow-y-auto border-border bg-popover text-foreground sm:max-w-6xl">
          <DialogHeader>
            <DialogTitle className="text-foreground">
              {selectedDriver?.driver.name} &mdash; {driverFrom === driverTo ? driverFrom : `${driverFrom} → ${driverTo}`}
            </DialogTitle>
          </DialogHeader>

          {selectedDriver && (
            <div className="space-y-3 py-2">
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted">
                      <TableHead className="text-muted-foreground text-xs">Job Ref</TableHead>
                      <TableHead className="text-muted-foreground text-xs">Date</TableHead>
                      <TableHead className="text-muted-foreground text-xs">Type</TableHead>
                      <TableHead className="text-muted-foreground text-xs text-right">Pax</TableHead>
                      <TableHead className="text-muted-foreground text-xs">Route</TableHead>
                      <TableHead className="text-muted-foreground text-xs">Agent</TableHead>
                      <TableHead className="text-muted-foreground text-xs">Status</TableHead>
                      <TableHead className="text-muted-foreground text-xs text-center">
                        Att<br/><span className="text-[10px] font-normal opacity-75">30pt</span>
                      </TableHead>
                      <TableHead className="text-muted-foreground text-xs text-center">
                        App<br/><span className="text-[10px] font-normal opacity-75">20pt</span>
                      </TableHead>
                      <TableHead className="text-muted-foreground text-xs text-center">
                        Car<br/><span className="text-[10px] font-normal opacity-75">10pt</span>
                      </TableHead>
                      <TableHead className="text-muted-foreground text-xs text-center">
                        Maint<br/><span className="text-[10px] font-normal opacity-75">10pt</span>
                      </TableHead>
                      <TableHead className="text-muted-foreground text-xs text-center">
                        Work<br/><span className="text-[10px] font-normal opacity-75">30pt</span>
                      </TableHead>
                      <TableHead className="text-muted-foreground text-xs text-right">Score</TableHead>
                      <TableHead className="text-muted-foreground text-xs text-center">Missed</TableHead>
                      <TableHead className="text-muted-foreground text-xs text-right">Fee</TableHead>
                      <TableHead className="text-muted-foreground text-xs text-right">Deductions</TableHead>
                      <TableHead className="text-muted-foreground text-xs">Eval</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedDriver.trips.map((trip, idx) => {
                      const jobId = trip.jobId;
                      const currentScore = driverScoreEdits[jobId] ?? trip.driverJobScore;
                      const isSaving = driverScoreSaving[jobId] ?? false;
                      const isCompleted = trip.status === "COMPLETED";
                      const isMissing = !currentScore;
                      const isMissed = driverMissedJobs[jobId] ?? false;

                      const toggleDriverScore = (field: keyof Omit<DriverJobScore, "total" | "evaluation">) => {
                        const base = currentScore ?? { attendance: false, appearance: false, carCleanliness: false, maintenance: false, work: false, total: 0, evaluation: "Poor" };
                        const next = {
                          attendance: base.attendance,
                          appearance: base.appearance,
                          carCleanliness: base.carCleanliness,
                          maintenance: base.maintenance,
                          work: base.work,
                          [field]: !base[field],
                        };
                        saveDriverScore(jobId, next);
                      };

                      const evalColor =
                        currentScore?.evaluation === "Excellent" ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" :
                        currentScore?.evaluation === "Good" ? "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20" :
                        currentScore?.evaluation === "Average" ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20" :
                        currentScore?.evaluation === "Poor" ? "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20" : "";

                      return (
                        <TableRow
                          key={jobId}
                          className={`border-border ${isMissing ? "bg-amber-500/5 border-l-2 border-l-amber-500" : idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                        >
                          <TableCell className="text-foreground font-mono text-xs">{trip.internalRef}</TableCell>
                          <TableCell className="text-muted-foreground text-xs">{formatDate(trip.jobDate)}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">{trip.serviceType}</Badge>
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground text-xs">{trip.paxCount}</TableCell>
                          <TableCell className="text-muted-foreground text-xs whitespace-nowrap">{trip.route}</TableCell>
                          <TableCell className="text-muted-foreground text-xs">{trip.agent}</TableCell>
                          <TableCell>
                            <StatusBadge status={trip.status} />
                          </TableCell>
                          {/* Attendance — 30pt */}
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              disabled={isSaving}
                              checked={currentScore?.attendance ?? false}
                              onChange={() => toggleDriverScore("attendance")}
                              title="Attendance (30pt)"
                              className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                            />
                          </TableCell>
                          {/* Appearance — 20pt */}
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              disabled={isSaving}
                              checked={currentScore?.appearance ?? false}
                              onChange={() => toggleDriverScore("appearance")}
                              title="Appearance (20pt)"
                              className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                            />
                          </TableCell>
                          {/* Car Cleanliness — 10pt */}
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              disabled={isSaving}
                              checked={currentScore?.carCleanliness ?? false}
                              onChange={() => toggleDriverScore("carCleanliness")}
                              title="Car Cleanliness (10pt)"
                              className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                            />
                          </TableCell>
                          {/* Maintenance — 10pt */}
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              disabled={isSaving}
                              checked={currentScore?.maintenance ?? false}
                              onChange={() => toggleDriverScore("maintenance")}
                              title="Maintenance (10pt)"
                              className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                            />
                          </TableCell>
                          {/* Work — 20pt, auto from COMPLETED */}
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              disabled={isSaving}
                              checked={currentScore?.work ?? false}
                              onChange={() => toggleDriverScore("work")}
                              title={isCompleted ? "Work (20pt) — COMPLETED" : "Work (20pt)"}
                              className="h-4 w-4 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed accent-emerald-600"
                            />
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm font-semibold">
                            {isSaving ? (
                              <Loader2 className="h-3 w-3 animate-spin inline" />
                            ) : currentScore ? (
                              <span>{currentScore.total}<span className="text-muted-foreground text-xs">/100</span></span>
                            ) : (
                              <span className="text-amber-500 text-xs">—</span>
                            )}
                          </TableCell>
                          {/* Missed */}
                          <TableCell className="text-center">
                            <input
                              type="checkbox"
                              checked={isMissed}
                              onChange={() => setDriverMissedJobs((prev) => ({ ...prev, [jobId]: !isMissed }))}
                              title="Mark as missed (excludes fee from total)"
                              className="h-4 w-4 cursor-pointer accent-red-600"
                            />
                          </TableCell>
                          {/* Trip Fee */}
                          <TableCell className="text-right font-mono font-medium text-sm">
                            {isMissed ? (
                              <span className="text-muted-foreground">—</span>
                            ) : trip.tripFee != null ? (
                              <span className="flex flex-col items-end gap-0">
                                {trip.tariffFee != null && trip.tariffFee !== trip.tripFee && (
                                  <span className="text-muted-foreground line-through text-xs">
                                    {fmt(trip.tariffFee, locale)}
                                  </span>
                                )}
                                <span className={trip.tripFee > 0 ? "text-emerald-600 dark:text-emerald-400 font-semibold" : "text-muted-foreground"}>
                                  {fmt(trip.tripFee, locale)}
                                </span>
                              </span>
                            ) : (
                              <span className="text-amber-500 text-xs">—</span>
                            )}
                          </TableCell>
                          {/* Deductions */}
                          <TableCell className="text-right">
                            <input
                              type="number"
                              value={driverDeductions[jobId] ?? ""}
                              onChange={(e) => setDriverDeductions((prev) => ({ ...prev, [jobId]: Number(e.target.value) }))}
                              placeholder="0"
                              className="w-20 text-right text-sm bg-transparent border border-border rounded px-1 py-0.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </TableCell>
                          <TableCell>
                            {currentScore?.evaluation ? (
                              <Badge variant="outline" className={`text-xs ${evalColor}`}>
                                {currentScore.evaluation}
                              </Badge>
                            ) : <span className="text-xs text-amber-500">Pending</span>}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Summary footer */}
              <div className="flex justify-between items-center border-t border-border pt-3 px-1">
                <span className="text-sm font-semibold text-foreground">
                  {selectedDriver.tripCount} trips &mdash; {selectedDriver.tripCount - selectedDriver.missingScores} scored
                  {selectedDriver.missingScores > 0 && (
                    <span className="ml-2 text-amber-500 text-xs">({selectedDriver.missingScores} pending)</span>
                  )}
                </span>
                <div className="text-right">
                  {selectedDriver.avgScore !== null && (
                    <div className="text-xs text-muted-foreground">
                      Avg Score: <span className="font-semibold font-mono text-foreground">{selectedDriver.avgScore}/100</span>
                    </div>
                  )}
                  {(() => {
                    const netFees = selectedDriver.trips.reduce((sum, trip) => {
                      // Missed removes the trip fee, but a deduction still applies
                      // independently (deductions are untied from the Missed flag).
                      const fee = driverMissedJobs[trip.jobId] ? 0 : (trip.tripFee ?? 0);
                      const ded = driverDeductions[trip.jobId] ?? 0;
                      return sum + fee - ded;
                    }, 0);
                    const hasAdjustments = Object.keys(driverMissedJobs).some(k => driverMissedJobs[k]) || Object.values(driverDeductions).some(v => v > 0);
                    return (
                      <>
                        {hasAdjustments && (
                          <div className="text-xs text-muted-foreground line-through">
                            {fmt(selectedDriver.totalFees, locale)} EGP
                          </div>
                        )}
                        <span className="text-base font-medium text-emerald-600 dark:text-emerald-400 font-mono">
                          {fmt(netFees, locale)} EGP
                        </span>
                      </>
                    );
                  })()}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Hidden print content for PDF exports */}

      {/* Daily Dispatch Print */}
      {dispatchData && (
        <div ref={dispatchPrintRef} className="hidden">
          <h1>Daily Dispatch Summary</h1>
          <h2>Date: {dispatchDate}</h2>
          <dl className="info-grid">
            <dt>Total Jobs</dt><dd>{dispatchData.totalJobs}</dd>
            <dt>Assigned</dt><dd>{dispatchData.assignedCount} ({dispatchData.assignmentRate}%)</dd>
            <dt>Unassigned</dt><dd>{dispatchData.unassignedCount}</dd>
            <dt>Completion Rate</dt><dd>{dispatchData.completionRate}%</dd>
          </dl>
          <table>
            <thead>
              <tr><th>Ref</th><th>Type</th><th>Agent/Customer</th><th>Pax</th><th>Vehicle</th><th>Driver</th><th>Status</th></tr>
            </thead>
            <tbody>
              {dispatchData.jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.internalRef}</td>
                  <td>{job.serviceType}</td>
                  <td>{job.agent?.legalName || job.customer?.legalName || "\u2014"}</td>
                  <td className="text-right">{job.paxCount}</td>
                  <td>{job.assignment?.vehicle?.plateNumber || "\u2014"}</td>
                  <td>{job.assignment?.driver?.name || "\u2014"}</td>
                  <td>{job.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Driver Trips Print */}
      {driverData && (
        <div ref={driverPrintRef} className="hidden">
          <h1>Driver Trip Report</h1>
          <h2>Period: {driverFrom} to {driverTo}</h2>
          <dl className="info-grid">
            <dt>Total Drivers</dt><dd>{driverData.totalDrivers}</dd>
            <dt>Total Trips</dt><dd>{driverData.totalTrips}</dd>
          </dl>
          <table>
            <thead>
              <tr><th>Driver</th><th>Mobile</th><th className="text-right">Trips</th><th className="text-right">Total Fees (EGP)</th></tr>
            </thead>
            <tbody>
              {driverData.drivers.map((d) => (
                <tr key={d.driver.id}>
                  <td>{d.driver.name}</td>
                  <td>{d.driver.mobileNumber}</td>
                  <td className="text-right">{d.tripCount}</td>
                  <td className="text-right">{fmt(d.totalFees, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Agent Statement Print */}
      {agentData && (
        <div ref={agentPrintRef} className="hidden">
          <h1>Agent Statement</h1>
          <h2>{agentData.agent.legalName} {agentData.agent.tradeName ? `(${agentData.agent.tradeName})` : ""}</h2>
          <dl className="info-grid">
            <dt>Period</dt><dd>{agentData.period.from} to {agentData.period.to}</dd>
            <dt>Jobs</dt><dd>{agentData.jobCount}</dd>
            <dt>Total Invoiced</dt><dd>{fmt(agentData.totalInvoiced, locale)} {agentData.agent.currency}</dd>
            <dt>Total Paid</dt><dd>{fmt(agentData.totalPaid, locale)} {agentData.agent.currency}</dd>
            <dt>Outstanding</dt><dd>{fmt(agentData.outstandingBalance, locale)} {agentData.agent.currency}</dd>
            {agentData.agent.creditLimit !== null && <><dt>Credit Limit</dt><dd>{fmt(agentData.agent.creditLimit, locale)}</dd></>}
            {agentData.agent.creditDays !== null && <><dt>Credit Days</dt><dd>{agentData.agent.creditDays}</dd></>}
          </dl>
          <table>
            <thead>
              <tr><th>Invoice #</th><th>Date</th><th>Due Date</th><th className="text-right">Total</th><th className="text-right">Paid</th><th className="text-right">Balance</th><th>Status</th></tr>
            </thead>
            <tbody>
              {agentData.invoices.map((inv) => (
                <tr key={inv.invoiceNumber}>
                  <td>{inv.invoiceNumber}</td>
                  <td>{formatDate(inv.invoiceDate)}</td>
                  <td>{formatDate(inv.dueDate)}</td>
                  <td className="text-right">{fmt(inv.total, locale)}</td>
                  <td className="text-right">{fmt(inv.paid, locale)}</td>
                  <td className="text-right">{fmt(inv.balance, locale)}</td>
                  <td>{inv.status}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td colSpan={3}>Totals</td>
                <td className="text-right">{fmt(agentData.totalInvoiced, locale)}</td>
                <td className="text-right">{fmt(agentData.totalPaid, locale)}</td>
                <td className="text-right">{fmt(agentData.outstandingBalance, locale)}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Revenue Print */}
      {revenueData && (
        <div ref={revenuePrintRef} className="hidden">
          <h1>Revenue Report</h1>
          <h2>Period: {revenueData.period.from} to {revenueData.period.to}</h2>
          <dl className="info-grid">
            <dt>Total Revenue</dt><dd>{fmt(revenueData.totalRevenue, locale)}</dd>
            <dt>Total Costs</dt><dd>{fmt(revenueData.totalCosts, locale)}</dd>
            <dt>Gross Profit</dt><dd>{fmt(revenueData.grossProfit, locale)}</dd>
            <dt>Profit Margin</dt><dd>{revenueData.profitMargin}%</dd>
            <dt>Driver Fees</dt><dd>{fmt(revenueData.costBreakdown.driverFees, locale)}</dd>
            <dt>Rep Fees</dt><dd>{fmt(revenueData.costBreakdown.repFees, locale)}</dd>
            <dt>Supplier Costs</dt><dd>{fmt(revenueData.costBreakdown.supplierCosts, locale)}</dd>
          </dl>
          <h3>Revenue by Agent</h3>
          <table>
            <thead>
              <tr><th>Agent / Customer</th><th className="text-right">Revenue</th><th className="text-right">Invoices</th><th className="text-right">Jobs</th></tr>
            </thead>
            <tbody>
              {revenueData.byAgent.map((a) => (
                <tr key={a.agentId}>
                  <td>{a.name}</td>
                  <td className="text-right">{fmt(a.revenue, locale)}</td>
                  <td className="text-right">{a.invoiceCount}</td>
                  <td className="text-right">{a.jobCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Revenue by Service Type</h3>
          <table>
            <thead><tr><th>Service Type</th><th className="text-right">Revenue</th></tr></thead>
            <tbody>
              {Object.entries(revenueData.byServiceType).map(([type, amount]) => (
                <tr key={type}><td>{type}</td><td className="text-right">{fmt(amount, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Vehicle Compliance Print */}
      {complianceData.length > 0 && (
        <div ref={compliancePrintRef} className="hidden">
          <h1>Vehicle Compliance Report</h1>
          <table>
            <thead>
              <tr><th>Plate</th><th>Type</th><th>Ownership</th><th>License Expiry</th><th>Insurance</th><th>Insurance Expiry</th><th className="text-right">Annual Payment</th><th className="text-right">Total Fees</th></tr>
            </thead>
            <tbody>
              {complianceData.map((v, idx) => (
                <tr key={v.vehicleId || idx}>
                  <td>{v.plateNumber}</td>
                  <td>{v.vehicleTypeName}</td>
                  <td>{v.ownership}</td>
                  <td>{v.licenseExpiryDate ? formatDate(v.licenseExpiryDate) : "\u2014"}</td>
                  <td>{v.hasInsurance ? "Yes" : "No"}</td>
                  <td>{v.insuranceExpiryDate ? formatDate(v.insuranceExpiryDate) : "\u2014"}</td>
                  <td className="text-right">{v.annualPayment != null ? fmt(Number(v.annualPayment)) : "\u2014"}</td>
                  <td className="text-right">{v.totalFees != null ? fmt(Number(v.totalFees)) : "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Rep Fees Print */}
      {repFeeData && (
        <div ref={printRef} className="hidden">
          <h1>Rep Fees Report</h1>
          <h2>Period: {repFeeFrom} to {repFeeTo}</h2>
          <table>
            <thead>
              <tr>
                <th>Rep Name</th>
                <th className="text-right">Fee/Flight</th>
                <th className="text-right">Flights</th>
                <th className="text-right">Total (EGP)</th>
              </tr>
            </thead>
            <tbody>
              {repFeeData.reps.map((rep) => (
                <tr key={rep.repId}>
                  <td>{rep.repName}</td>
                  <td className="text-right">{fmt(rep.feePerFlight, locale)}</td>
                  <td className="text-right">{rep.flightCount}</td>
                  <td className="text-right">{fmt(rep.totalAmount, locale)}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td>Grand Total</td>
                <td />
                <td className="text-right">{repFeeData.totalFlights}</td>
                <td className="text-right">{fmt(repFeeData.grandTotal, locale)}</td>
              </tr>
            </tbody>
          </table>

          {repFeeData.reps.map((rep) => (
            <div key={rep.repId}>
              <h2>{rep.repName} - Details</h2>
              <table>
                <thead>
                  <tr>
                    <th>Flight No</th>
                    <th>Carrier</th>
                    <th>Job Ref</th>
                    <th className="text-right">Pax</th>
                    <th>Route</th>
                    <th>Hotel</th>
                    <th className="text-right">Fee (EGP)</th>
                  </tr>
                </thead>
                <tbody>
                  {rep.fees.map((fee) => (
                    <tr key={fee.id}>
                      <td>{fee.trafficJob.flight?.flightNo || "\u2014"}</td>
                      <td>{fee.trafficJob.flight?.carrier || "\u2014"}</td>
                      <td>{fee.trafficJob.internalRef}</td>
                      <td className="text-right">{fee.trafficJob.paxCount}</td>
                      <td>
                        {(fee.trafficJob.originAirport?.code || fee.trafficJob.fromZone?.name || fee.trafficJob.originZone?.name || fee.trafficJob.originHotel?.name || "\u2014")}{" \u2192 "}{(fee.trafficJob.destinationAirport?.code || fee.trafficJob.toZone?.name || fee.trafficJob.destinationZone?.name || fee.trafficJob.destinationHotel?.name || "\u2014")}
                      </td>
                      <td>{fee.trafficJob.hotel?.name || "\u2014"}</td>
                      <td className="text-right">{fmt(Number(fee.amount), locale)}</td>
                    </tr>
                  ))}
                  <tr className="total-row">
                    <td colSpan={6}>Subtotal</td>
                    <td className="text-right">{fmt(rep.totalAmount, locale)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      <JobDetailModal
        jobId={jobDetailId}
        open={jobDetailId !== null}
        onClose={() => setJobDetailId(null)}
      />
    </div>
  );
}
