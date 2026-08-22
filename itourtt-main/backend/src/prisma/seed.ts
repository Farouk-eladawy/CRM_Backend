import 'dotenv/config';
import * as bcrypt from 'bcryptjs';
import { PrismaClient } from '../../generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
import { seedEgyptLocations } from './seed-egypt-locations.js';

async function main() {
  const pool = new pg.Pool({
    connectionString: process.env.DATABASE_URL,
  });
  const adapter = new PrismaPg(pool);
  const prisma = new (PrismaClient as any)({ adapter });

  try {
    // Create default admin user
    const passwordHash = await bcrypt.hash('Admin@123', 12);

    const admin = await prisma.user.upsert({
      where: { email: 'admin@itour.local' },
      update: {},
      create: {
        email: 'admin@itour.local',
        passwordHash,
        name: 'System Admin',
        role: 'ADMIN',
        isActive: true,
      },
    });

    console.log(`Admin user created: ${admin.email} (${admin.id})`);

    // Create super admin
    const superAdminHash = await bcrypt.hash('Win16@64_PineBlue', 12);

    const superAdmin = await prisma.user.upsert({
      where: { email: 'mggouda@gmail.com' },
      update: {},
      create: {
        email: 'mggouda@gmail.com',
        passwordHash: superAdminHash,
        name: 'Mohamed Gouda',
        role: 'ADMIN',
        isActive: true,
      },
    });

    console.log(`Super admin created: ${superAdmin.email} (${superAdmin.id})`);

    // ─── SEED SYSTEM ROLES ───
    // Permissions captured from production on 2026-04-07.
    // Admin has no permission rows — full access is granted via role guard.
    // Driver and Rep have no permissions — portal-only accounts.
    const systemRoles: Array<{ name: string; slug: string; description: string; permissions: string[] }> = [
      {
        name: 'Admin',
        slug: 'admin',
        description: 'Full system access',
        permissions: [],
      },
      {
        name: 'Accountant',
        slug: 'accountant',
        description: 'Handles finance and financial reports',
        permissions: [
          'activity-logs','activity-logs.export',
          'agents','agents.addButton','agents.downloadTemplate','agents.export','agents.form',
          'agents.form.contactInfo','agents.form.creditDays','agents.form.creditLimit',
          'agents.form.currency','agents.form.legalName','agents.form.refPattern',
          'agents.form.taxId','agents.form.tradeName','agents.import','agents.table',
          'agents.table.deleteButton','agents.table.editButton','agents.table.toggleStatus',
          'customers','customers.addButton','customers.detail',
          'customers.detail.importTemplates','customers.detail.importTemplates.delete',
          'customers.detail.importTemplates.upload','customers.detail.priceList',
          'customers.detail.priceList.addRoute','customers.detail.priceList.deleteRoute',
          'customers.detail.priceList.downloadTemplate','customers.detail.priceList.editPrice',
          'customers.detail.priceList.import','customers.detail.priceList.saveAll',
          'customers.downloadTemplate','customers.export','customers.form',
          'customers.form.contactInfo','customers.form.creditDays','customers.form.creditLimit',
          'customers.form.currency','customers.form.legalName','customers.form.taxId',
          'customers.form.tradeName','customers.import','customers.table',
          'customers.table.deleteButton','customers.table.editButton',
          'customers.table.toggleStatus','customers.table.viewButton',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'finance','finance.exports','finance.exports.collections','finance.exports.customers',
          'finance.exports.invoices','finance.exports.journals','finance.exports.payments',
          'finance.exports.suppliers','finance.exports.vendorBills',
          'finance.invoices','finance.invoices.addButton','finance.invoices.detail',
          'finance.invoices.detail.addLine','finance.invoices.detail.applyVat',
          'finance.invoices.detail.cancelButton','finance.invoices.detail.deleteLine',
          'finance.invoices.detail.editLines','finance.invoices.detail.postButton',
          'finance.invoices.recordPayment','finance.b2cInvoices','finance.odooExport',
          'finance.payments','finance.payments.addButton','finance.payments.deleteButton',
          'reports','reports.agentStatement','reports.dailyDispatch','reports.driverScore',
          'reports.driverTrips','reports.evidence','reports.flightDelay','reports.jobStatus',
          'reports.repFees','reports.repScore','reports.guestSurveys','reports.revenue',
          'reports.carJobs','reports.supplierJobs','reports.vehicleCompliance','reports.review',
          'suppliers','suppliers.addButton','suppliers.downloadTemplate','suppliers.export',
          'suppliers.form','suppliers.form.contactInfo','suppliers.form.legalName',
          'suppliers.form.taxId','suppliers.form.tradeName','suppliers.import','suppliers.table',
          'suppliers.table.createAccount','suppliers.table.deleteButton',
          'suppliers.table.editButton','suppliers.table.resetPassword',
          'suppliers.table.toggleStatus',
        ],
      },
      {
        name: 'Agent Manager',
        slug: 'agent-manager',
        description: 'Manages agents, customers, and bookings',
        permissions: [
          'activity-logs','activity-logs.export',
          'agents','agents.addButton','agents.downloadTemplate','agents.export','agents.form',
          'agents.form.contactInfo','agents.form.creditDays','agents.form.creditLimit',
          'agents.form.currency','agents.form.legalName','agents.form.refPattern',
          'agents.form.taxId','agents.form.tradeName','agents.import','agents.table',
          'agents.table.deleteButton','agents.table.editButton','agents.table.toggleStatus',
          'customers','customers.addButton','customers.detail',
          'customers.detail.importTemplates','customers.detail.importTemplates.delete',
          'customers.detail.importTemplates.upload','customers.detail.priceList',
          'customers.detail.priceList.addRoute','customers.detail.priceList.deleteRoute',
          'customers.detail.priceList.downloadTemplate','customers.detail.priceList.editPrice',
          'customers.detail.priceList.import','customers.detail.priceList.saveAll',
          'customers.downloadTemplate','customers.export','customers.form',
          'customers.form.contactInfo','customers.form.creditDays','customers.form.creditLimit',
          'customers.form.currency','customers.form.legalName','customers.form.taxId',
          'customers.form.tradeName','customers.import','customers.table',
          'customers.table.deleteButton','customers.table.editButton',
          'customers.table.toggleStatus','customers.table.viewButton',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'traffic-jobs',
          'traffic-jobs.b2b','traffic-jobs.b2b.createJob','traffic-jobs.b2b.form',
          'traffic-jobs.b2b.form.customer','traffic-jobs.b2b.form.dateTime',
          'traffic-jobs.b2b.form.flightInfo','traffic-jobs.b2b.form.meetingInfo',
          'traffic-jobs.b2b.form.notes','traffic-jobs.b2b.form.paxCount',
          'traffic-jobs.b2b.form.route','traffic-jobs.b2b.form.serviceType',
          'traffic-jobs.b2b.importJobs','traffic-jobs.b2b.table',
          'traffic-jobs.b2b.table.statusFilter',
          'traffic-jobs.online','traffic-jobs.online.createJob','traffic-jobs.online.form',
          'traffic-jobs.online.form.agentRef','traffic-jobs.online.form.clientInfo',
          'traffic-jobs.online.form.dateTime','traffic-jobs.online.form.extras',
          'traffic-jobs.online.form.flightInfo','traffic-jobs.online.form.notes',
          'traffic-jobs.online.form.paxCount','traffic-jobs.online.form.printSign',
          'traffic-jobs.online.form.provider','traffic-jobs.online.form.requestedVehicleType',
          'traffic-jobs.online.form.route','traffic-jobs.online.form.serviceType',
          'traffic-jobs.online.table','traffic-jobs.online.table.statusFilter',
        ],
      },
      {
        name: 'Dispatch Manager',
        slug: 'dispatch-manager',
        description: 'Manages dispatch team and operations',
        permissions: [
          'activity-logs','activity-logs.export',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'dispatch','dispatch.assignment','dispatch.assignment.assignDriver',
          'dispatch.assignment.assignRep','dispatch.assignment.assignVehicle',
          'dispatch.assignment.changeStatus','dispatch.assignment.unassign',
          'dispatch.assignment.unlock48h','dispatch.datePicker','dispatch.exportButton',
          'dispatch.grid',
          'drivers','drivers.addButton','drivers.downloadTemplate','drivers.export',
          'drivers.form','drivers.form.licenseExpiry','drivers.form.licenseNumber',
          'drivers.form.mobile','drivers.form.name','drivers.import','drivers.table',
          'drivers.table.createAccount','drivers.table.deleteButton','drivers.table.editButton',
          'drivers.table.resetPassword','drivers.table.toggleStatus',
          'drivers.table.uploadAttachment',
          'locations','locations.airports','locations.airports.addButton',
          'locations.airports.deleteButton','locations.airports.editButton',
          'locations.cities','locations.cities.addButton','locations.cities.deleteButton',
          'locations.cities.editButton','locations.countries','locations.countries.addButton',
          'locations.countries.editButton','locations.downloadTemplate','locations.export',
          'locations.hotels','locations.hotels.addButton','locations.hotels.deleteButton',
          'locations.hotels.editButton','locations.import','locations.zones',
          'locations.zones.addButton','locations.zones.deleteButton','locations.zones.editButton',
          'reports','reports.agentStatement','reports.dailyDispatch','reports.driverScore',
          'reports.driverTrips','reports.evidence','reports.flightDelay','reports.jobStatus',
          'reports.repFees','reports.repScore','reports.guestSurveys','reports.revenue',
          'reports.carJobs','reports.supplierJobs','reports.vehicleCompliance','reports.review',
          'reps','reps.addButton','reps.downloadTemplate','reps.export','reps.form',
          'reps.form.feePerFlight','reps.form.mobile','reps.form.name','reps.import',
          'reps.table','reps.table.createAccount','reps.table.deleteButton',
          'reps.table.editButton','reps.table.resetPassword','reps.table.toggleStatus',
          'reps.table.uploadAttachment',
          'suppliers','suppliers.addButton','suppliers.downloadTemplate','suppliers.export',
          'suppliers.form','suppliers.form.contactInfo','suppliers.form.legalName',
          'suppliers.form.taxId','suppliers.form.tradeName','suppliers.import','suppliers.table',
          'suppliers.table.createAccount','suppliers.table.deleteButton',
          'suppliers.table.editButton','suppliers.table.resetPassword',
          'suppliers.table.toggleStatus',
          'traffic-jobs',
          'traffic-jobs.b2b','traffic-jobs.b2b.createJob','traffic-jobs.b2b.form',
          'traffic-jobs.b2b.form.customer','traffic-jobs.b2b.form.dateTime',
          'traffic-jobs.b2b.form.flightInfo','traffic-jobs.b2b.form.meetingInfo',
          'traffic-jobs.b2b.form.notes','traffic-jobs.b2b.form.paxCount',
          'traffic-jobs.b2b.form.route','traffic-jobs.b2b.form.serviceType',
          'traffic-jobs.b2b.importJobs','traffic-jobs.b2b.table',
          'traffic-jobs.b2b.table.statusFilter',
          'traffic-jobs.online','traffic-jobs.online.createJob','traffic-jobs.online.form',
          'traffic-jobs.online.form.agentRef','traffic-jobs.online.form.clientInfo',
          'traffic-jobs.online.form.dateTime','traffic-jobs.online.form.extras',
          'traffic-jobs.online.form.flightInfo','traffic-jobs.online.form.notes',
          'traffic-jobs.online.form.paxCount','traffic-jobs.online.form.printSign',
          'traffic-jobs.online.form.provider','traffic-jobs.online.form.requestedVehicleType',
          'traffic-jobs.online.form.route','traffic-jobs.online.form.serviceType',
          'traffic-jobs.online.table','traffic-jobs.online.table.statusFilter',
          'vehicles','vehicles.addButton','vehicles.downloadTemplate','vehicles.export',
          'vehicles.form','vehicles.form.brand','vehicles.form.color',
          'vehicles.form.luggageCapacity','vehicles.form.makeYear','vehicles.form.model',
          'vehicles.form.ownership','vehicles.form.plateNumber','vehicles.form.vehicleType',
          'vehicles.import','vehicles.table','vehicles.table.deleteButton',
          'vehicles.table.editButton','vehicles.table.toggleStatus',
          'vehicles.types','vehicles.types.addButton','vehicles.types.editButton',
        ],
      },
      {
        name: 'Dispatch Operator',
        slug: 'dispatch-operator',
        description: 'Handles dispatch operations',
        permissions: [
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'dispatch','dispatch.assignment','dispatch.assignment.assignDriver',
          'dispatch.assignment.assignVehicle','dispatch.assignment.changeStatus',
          'dispatch.assignment.unassign','dispatch.assignment.unlock48h',
          'dispatch.datePicker','dispatch.exportButton','dispatch.grid',
          'drivers','drivers.addButton','drivers.downloadTemplate','drivers.export',
          'drivers.form','drivers.form.licenseExpiry','drivers.form.licenseNumber',
          'drivers.form.mobile','drivers.form.name','drivers.import','drivers.table',
          'drivers.table.createAccount','drivers.table.deleteButton','drivers.table.editButton',
          'drivers.table.resetPassword','drivers.table.toggleStatus',
          'drivers.table.uploadAttachment',
          'locations','locations.airports','locations.airports.addButton',
          'locations.airports.deleteButton','locations.airports.editButton',
          'locations.cities','locations.cities.addButton','locations.cities.deleteButton',
          'locations.cities.editButton','locations.countries','locations.countries.addButton',
          'locations.countries.editButton','locations.downloadTemplate','locations.export',
          'locations.hotels','locations.hotels.addButton','locations.hotels.deleteButton',
          'locations.hotels.editButton','locations.import','locations.zones',
          'locations.zones.addButton','locations.zones.deleteButton','locations.zones.editButton',
          'reps','reps.addButton','reps.downloadTemplate','reps.export','reps.form',
          'reps.form.feePerFlight','reps.form.mobile','reps.form.name','reps.import',
          'reps.table','reps.table.createAccount','reps.table.deleteButton',
          'reps.table.editButton','reps.table.resetPassword','reps.table.toggleStatus',
          'reps.table.uploadAttachment',
          'traffic-jobs',
          'traffic-jobs.b2b','traffic-jobs.b2b.createJob','traffic-jobs.b2b.form',
          'traffic-jobs.b2b.form.customer','traffic-jobs.b2b.form.dateTime',
          'traffic-jobs.b2b.form.flightInfo','traffic-jobs.b2b.form.meetingInfo',
          'traffic-jobs.b2b.form.notes','traffic-jobs.b2b.form.paxCount',
          'traffic-jobs.b2b.form.route','traffic-jobs.b2b.form.serviceType',
          'traffic-jobs.b2b.importJobs','traffic-jobs.b2b.table',
          'traffic-jobs.b2b.table.statusFilter',
          'traffic-jobs.online','traffic-jobs.online.createJob','traffic-jobs.online.form',
          'traffic-jobs.online.form.agentRef','traffic-jobs.online.form.clientInfo',
          'traffic-jobs.online.form.dateTime','traffic-jobs.online.form.extras',
          'traffic-jobs.online.form.flightInfo','traffic-jobs.online.form.notes',
          'traffic-jobs.online.form.paxCount','traffic-jobs.online.form.printSign',
          'traffic-jobs.online.form.provider','traffic-jobs.online.form.requestedVehicleType',
          'traffic-jobs.online.form.route','traffic-jobs.online.form.serviceType',
          'traffic-jobs.online.table','traffic-jobs.online.table.statusFilter',
          'vehicles','vehicles.addButton','vehicles.downloadTemplate','vehicles.export',
          'vehicles.form','vehicles.form.brand','vehicles.form.color',
          'vehicles.form.luggageCapacity','vehicles.form.makeYear','vehicles.form.model',
          'vehicles.form.ownership','vehicles.form.plateNumber','vehicles.form.vehicleType',
          'vehicles.import','vehicles.table','vehicles.table.deleteButton',
          'vehicles.table.editButton','vehicles.table.toggleStatus',
          'vehicles.types','vehicles.types.addButton','vehicles.types.editButton',
        ],
      },
      {
        name: 'Dispatcher',
        slug: 'dispatcher',
        description: 'Controls traffic jobs and dispatch operations',
        permissions: [
          'activity-logs','activity-logs.export',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'dispatch','dispatch.assignment','dispatch.assignment.assignDriver',
          'dispatch.assignment.assignRep','dispatch.assignment.assignVehicle',
          'dispatch.assignment.changeStatus','dispatch.assignment.unassign',
          'dispatch.assignment.unlock48h','dispatch.datePicker','dispatch.exportButton',
          'dispatch.grid',
          'drivers','drivers.addButton','drivers.downloadTemplate','drivers.export',
          'drivers.form','drivers.form.licenseExpiry','drivers.form.licenseNumber',
          'drivers.form.mobile','drivers.form.name','drivers.import','drivers.table',
          'drivers.table.createAccount','drivers.table.deleteButton','drivers.table.editButton',
          'drivers.table.resetPassword','drivers.table.toggleStatus',
          'drivers.table.uploadAttachment',
          'locations','locations.airports','locations.airports.addButton',
          'locations.airports.deleteButton','locations.airports.editButton',
          'locations.cities','locations.cities.addButton','locations.cities.deleteButton',
          'locations.cities.editButton','locations.countries','locations.countries.addButton',
          'locations.countries.editButton','locations.downloadTemplate','locations.export',
          'locations.hotels','locations.hotels.addButton','locations.hotels.deleteButton',
          'locations.hotels.editButton','locations.import','locations.zones',
          'locations.zones.addButton','locations.zones.deleteButton','locations.zones.editButton',
          'reps','reps.addButton','reps.downloadTemplate','reps.export','reps.form',
          'reps.form.feePerFlight','reps.form.mobile','reps.form.name','reps.import',
          'reps.table','reps.table.createAccount','reps.table.deleteButton',
          'reps.table.editButton','reps.table.resetPassword','reps.table.toggleStatus',
          'reps.table.uploadAttachment',
          'reports','reports.agentStatement','reports.dailyDispatch','reports.driverScore',
          'reports.driverTrips','reports.evidence','reports.flightDelay','reports.jobStatus',
          'reports.repFees','reports.repScore','reports.guestSurveys','reports.revenue',
          'reports.carJobs','reports.supplierJobs','reports.vehicleCompliance','reports.review',
          'traffic-jobs',
          'traffic-jobs.b2b','traffic-jobs.b2b.createJob','traffic-jobs.b2b.form',
          'traffic-jobs.b2b.form.customer','traffic-jobs.b2b.form.dateTime',
          'traffic-jobs.b2b.form.flightInfo','traffic-jobs.b2b.form.meetingInfo',
          'traffic-jobs.b2b.form.notes','traffic-jobs.b2b.form.paxCount',
          'traffic-jobs.b2b.form.route','traffic-jobs.b2b.form.serviceType',
          'traffic-jobs.b2b.importJobs','traffic-jobs.b2b.table',
          'traffic-jobs.b2b.table.statusFilter',
          'traffic-jobs.online','traffic-jobs.online.createJob','traffic-jobs.online.form',
          'traffic-jobs.online.form.agentRef','traffic-jobs.online.form.clientInfo',
          'traffic-jobs.online.form.dateTime','traffic-jobs.online.form.extras',
          'traffic-jobs.online.form.flightInfo','traffic-jobs.online.form.notes',
          'traffic-jobs.online.form.paxCount','traffic-jobs.online.form.printSign',
          'traffic-jobs.online.form.provider','traffic-jobs.online.form.requestedVehicleType',
          'traffic-jobs.online.form.route','traffic-jobs.online.form.serviceType',
          'traffic-jobs.online.table','traffic-jobs.online.table.statusFilter',
          'vehicles','vehicles.addButton','vehicles.downloadTemplate','vehicles.export',
          'vehicles.form','vehicles.form.brand','vehicles.form.color',
          'vehicles.form.luggageCapacity','vehicles.form.makeYear','vehicles.form.model',
          'vehicles.form.ownership','vehicles.form.plateNumber','vehicles.form.vehicleType',
          'vehicles.import','vehicles.table','vehicles.table.deleteButton',
          'vehicles.table.editButton','vehicles.table.toggleStatus',
          'vehicles.types','vehicles.types.addButton','vehicles.types.editButton',
        ],
      },
      {
        name: 'Driver',
        slug: 'driver',
        description: 'Driver portal user',
        permissions: [],
      },
      {
        name: 'FC',
        slug: 'fc',
        description: 'Financial controller with oversight of all finance operations',
        permissions: [
          'activity-logs','activity-logs.export',
          'agents','agents.addButton','agents.downloadTemplate','agents.export','agents.form',
          'agents.form.contactInfo','agents.form.creditDays','agents.form.creditLimit',
          'agents.form.currency','agents.form.legalName','agents.form.refPattern',
          'agents.form.taxId','agents.form.tradeName','agents.import','agents.table',
          'agents.table.deleteButton','agents.table.editButton','agents.table.toggleStatus',
          'customers','customers.addButton','customers.detail',
          'customers.detail.importTemplates','customers.detail.importTemplates.delete',
          'customers.detail.importTemplates.upload','customers.detail.priceList',
          'customers.detail.priceList.addRoute','customers.detail.priceList.deleteRoute',
          'customers.detail.priceList.downloadTemplate','customers.detail.priceList.editPrice',
          'customers.detail.priceList.import','customers.detail.priceList.saveAll',
          'customers.downloadTemplate','customers.export','customers.form',
          'customers.form.contactInfo','customers.form.creditDays','customers.form.creditLimit',
          'customers.form.currency','customers.form.legalName','customers.form.taxId',
          'customers.form.tradeName','customers.import','customers.table',
          'customers.table.deleteButton','customers.table.editButton',
          'customers.table.toggleStatus','customers.table.viewButton',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'drivers','drivers.addButton','drivers.downloadTemplate','drivers.export',
          'drivers.form','drivers.form.licenseExpiry','drivers.form.licenseNumber',
          'drivers.form.mobile','drivers.form.name','drivers.import','drivers.table',
          'drivers.table.createAccount','drivers.table.deleteButton','drivers.table.editButton',
          'drivers.table.resetPassword','drivers.table.toggleStatus',
          'drivers.table.uploadAttachment',
          'finance','finance.exports','finance.exports.collections','finance.exports.customers',
          'finance.exports.invoices','finance.exports.journals','finance.exports.payments',
          'finance.exports.suppliers','finance.exports.vendorBills',
          'finance.invoices','finance.invoices.addButton','finance.invoices.detail',
          'finance.invoices.detail.addLine','finance.invoices.detail.applyVat',
          'finance.invoices.detail.cancelButton','finance.invoices.detail.deleteLine',
          'finance.invoices.detail.editLines','finance.invoices.detail.postButton',
          'finance.invoices.recordPayment','finance.b2cInvoices','finance.odooExport',
          'finance.payments','finance.payments.addButton','finance.payments.deleteButton',
          'reports','reports.agentStatement','reports.dailyDispatch','reports.driverScore',
          'reports.driverTrips','reports.evidence','reports.flightDelay','reports.jobStatus',
          'reports.repFees','reports.repScore','reports.guestSurveys','reports.revenue',
          'reports.carJobs','reports.supplierJobs','reports.vehicleCompliance','reports.review',
          'reps','reps.addButton','reps.downloadTemplate','reps.export','reps.form',
          'reps.form.feePerFlight','reps.form.mobile','reps.form.name','reps.import',
          'reps.table','reps.table.createAccount','reps.table.deleteButton',
          'reps.table.editButton','reps.table.resetPassword','reps.table.toggleStatus',
          'reps.table.uploadAttachment',
          'suppliers','suppliers.addButton','suppliers.downloadTemplate','suppliers.export',
          'suppliers.form','suppliers.form.contactInfo','suppliers.form.legalName',
          'suppliers.form.taxId','suppliers.form.tradeName','suppliers.import','suppliers.table',
          'suppliers.table.createAccount','suppliers.table.deleteButton',
          'suppliers.table.editButton','suppliers.table.resetPassword',
          'suppliers.table.toggleStatus',
        ],
      },
      {
        name: 'Online Manager',
        slug: 'online-manager',
        description: 'Manages online booking team and operations',
        permissions: [
          'activity-logs','activity-logs.export',
          'agents','agents.addButton','agents.downloadTemplate','agents.export','agents.form',
          'agents.form.contactInfo','agents.form.creditDays','agents.form.creditLimit',
          'agents.form.currency','agents.form.legalName','agents.form.refPattern',
          'agents.form.taxId','agents.form.tradeName','agents.import','agents.table',
          'agents.table.deleteButton','agents.table.editButton','agents.table.toggleStatus',
          'customers','customers.addButton','customers.detail',
          'customers.detail.importTemplates','customers.detail.importTemplates.delete',
          'customers.detail.importTemplates.upload','customers.detail.priceList',
          'customers.detail.priceList.addRoute','customers.detail.priceList.deleteRoute',
          'customers.detail.priceList.downloadTemplate','customers.detail.priceList.editPrice',
          'customers.detail.priceList.import','customers.detail.priceList.saveAll',
          'customers.downloadTemplate','customers.export','customers.form',
          'customers.form.contactInfo','customers.form.creditDays','customers.form.creditLimit',
          'customers.form.currency','customers.form.legalName','customers.form.taxId',
          'customers.form.tradeName','customers.import','customers.table',
          'customers.table.deleteButton','customers.table.editButton',
          'customers.table.toggleStatus','customers.table.viewButton',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'guest-bookings','guest-bookings.cancel','guest-bookings.convert',
          'locations','locations.airports','locations.airports.addButton',
          'locations.airports.deleteButton','locations.airports.editButton',
          'locations.cities','locations.cities.addButton','locations.cities.deleteButton',
          'locations.cities.editButton','locations.countries','locations.countries.addButton',
          'locations.countries.editButton','locations.downloadTemplate','locations.export',
          'locations.hotels','locations.hotels.addButton','locations.hotels.deleteButton',
          'locations.hotels.editButton','locations.import','locations.zones',
          'locations.zones.addButton','locations.zones.deleteButton','locations.zones.editButton',
          'reports','reports.agentStatement','reports.dailyDispatch','reports.driverScore',
          'reports.driverTrips','reports.evidence','reports.flightDelay','reports.jobStatus',
          'reports.repFees','reports.repScore','reports.guestSurveys','reports.revenue',
          'reports.carJobs','reports.supplierJobs','reports.vehicleCompliance','reports.review',
          'traffic-jobs',
          'traffic-jobs.b2b','traffic-jobs.b2b.createJob','traffic-jobs.b2b.form',
          'traffic-jobs.b2b.form.customer','traffic-jobs.b2b.form.dateTime',
          'traffic-jobs.b2b.form.flightInfo','traffic-jobs.b2b.form.meetingInfo',
          'traffic-jobs.b2b.form.notes','traffic-jobs.b2b.form.paxCount',
          'traffic-jobs.b2b.form.route','traffic-jobs.b2b.form.serviceType',
          'traffic-jobs.b2b.importJobs','traffic-jobs.b2b.table',
          'traffic-jobs.b2b.table.statusFilter',
          'traffic-jobs.online','traffic-jobs.online.createJob','traffic-jobs.online.form',
          'traffic-jobs.online.form.agentRef','traffic-jobs.online.form.clientInfo',
          'traffic-jobs.online.form.dateTime','traffic-jobs.online.form.extras',
          'traffic-jobs.online.form.flightInfo','traffic-jobs.online.form.notes',
          'traffic-jobs.online.form.paxCount','traffic-jobs.online.form.printSign',
          'traffic-jobs.online.form.provider','traffic-jobs.online.form.requestedVehicleType',
          'traffic-jobs.online.form.route','traffic-jobs.online.form.serviceType',
          'traffic-jobs.online.table','traffic-jobs.online.table.statusFilter',
        ],
      },
      {
        name: 'Online Operator',
        slug: 'online-operator',
        description: 'Handles online booking operations',
        permissions: [
          'agents','agents.addButton','agents.downloadTemplate','agents.export','agents.form',
          'agents.form.contactInfo','agents.form.creditDays','agents.form.creditLimit',
          'agents.form.currency','agents.form.legalName','agents.form.refPattern',
          'agents.form.taxId','agents.form.tradeName','agents.import','agents.table',
          'agents.table.deleteButton','agents.table.editButton','agents.table.toggleStatus',
          'customers','customers.addButton','customers.detail',
          'customers.detail.importTemplates','customers.detail.importTemplates.delete',
          'customers.detail.importTemplates.upload','customers.detail.priceList',
          'customers.detail.priceList.addRoute','customers.detail.priceList.deleteRoute',
          'customers.detail.priceList.downloadTemplate','customers.detail.priceList.editPrice',
          'customers.detail.priceList.import','customers.detail.priceList.saveAll',
          'customers.downloadTemplate','customers.export','customers.form',
          'customers.form.contactInfo','customers.form.creditDays','customers.form.creditLimit',
          'customers.form.currency','customers.form.legalName','customers.form.taxId',
          'customers.form.tradeName','customers.import','customers.table',
          'customers.table.deleteButton','customers.table.editButton',
          'customers.table.toggleStatus','customers.table.viewButton',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'dispatch','dispatch.assignment.assignRep',
          'guest-bookings','guest-bookings.cancel','guest-bookings.convert',
          'locations','locations.airports','locations.airports.addButton',
          'locations.airports.deleteButton','locations.airports.editButton',
          'locations.cities','locations.cities.addButton','locations.cities.deleteButton',
          'locations.cities.editButton','locations.countries','locations.countries.addButton',
          'locations.countries.editButton','locations.downloadTemplate','locations.export',
          'locations.hotels','locations.hotels.addButton','locations.hotels.deleteButton',
          'locations.hotels.editButton','locations.import','locations.zones',
          'locations.zones.addButton','locations.zones.deleteButton','locations.zones.editButton',
          'traffic-jobs',
          'traffic-jobs.b2b','traffic-jobs.b2b.createJob','traffic-jobs.b2b.form',
          'traffic-jobs.b2b.form.customer','traffic-jobs.b2b.form.dateTime',
          'traffic-jobs.b2b.form.flightInfo','traffic-jobs.b2b.form.meetingInfo',
          'traffic-jobs.b2b.form.notes','traffic-jobs.b2b.form.paxCount',
          'traffic-jobs.b2b.form.route','traffic-jobs.b2b.form.serviceType',
          'traffic-jobs.b2b.importJobs','traffic-jobs.b2b.table',
          'traffic-jobs.b2b.table.statusFilter',
          'traffic-jobs.online','traffic-jobs.online.createJob','traffic-jobs.online.form',
          'traffic-jobs.online.form.agentRef','traffic-jobs.online.form.clientInfo',
          'traffic-jobs.online.form.dateTime','traffic-jobs.online.form.extras',
          'traffic-jobs.online.form.flightInfo','traffic-jobs.online.form.notes',
          'traffic-jobs.online.form.paxCount','traffic-jobs.online.form.printSign',
          'traffic-jobs.online.form.provider','traffic-jobs.online.form.requestedVehicleType',
          'traffic-jobs.online.form.route','traffic-jobs.online.form.serviceType',
          'traffic-jobs.online.table','traffic-jobs.online.table.statusFilter',
        ],
      },
      {
        name: 'Rep',
        slug: 'rep',
        description: 'Field representative portal user',
        permissions: [],
      },
      {
        name: 'Transportation Accountant',
        slug: 'transportation-accountant',
        description: 'Handles transportation-specific accounting and costs',
        permissions: [
          'activity-logs','activity-logs.export',
          'dashboard','dashboard.recentJobs','dashboard.revenue','dashboard.stats',
          'drivers','drivers.addButton','drivers.downloadTemplate','drivers.export',
          'drivers.form','drivers.form.licenseExpiry','drivers.form.licenseNumber',
          'drivers.form.mobile','drivers.form.name','drivers.import','drivers.table',
          'drivers.table.createAccount','drivers.table.deleteButton','drivers.table.editButton',
          'drivers.table.resetPassword','drivers.table.toggleStatus',
          'drivers.table.uploadAttachment',
          'finance','finance.exports','finance.exports.collections','finance.exports.customers',
          'finance.exports.invoices','finance.exports.journals','finance.exports.payments',
          'finance.exports.suppliers','finance.exports.vendorBills',
          'finance.invoices','finance.invoices.addButton','finance.invoices.detail',
          'finance.invoices.detail.addLine','finance.invoices.detail.applyVat',
          'finance.invoices.detail.cancelButton','finance.invoices.detail.deleteLine',
          'finance.invoices.detail.editLines','finance.invoices.detail.postButton',
          'finance.invoices.recordPayment','finance.b2cInvoices','finance.odooExport',
          'finance.payments','finance.payments.addButton','finance.payments.deleteButton',
          'reports','reports.agentStatement','reports.dailyDispatch','reports.driverScore',
          'reports.driverTrips','reports.evidence','reports.flightDelay','reports.jobStatus',
          'reports.repFees','reports.repScore','reports.guestSurveys','reports.revenue',
          'reports.carJobs','reports.supplierJobs','reports.vehicleCompliance','reports.review',
          'suppliers','suppliers.addButton','suppliers.downloadTemplate','suppliers.export',
          'suppliers.form','suppliers.form.contactInfo','suppliers.form.legalName',
          'suppliers.form.taxId','suppliers.form.tradeName','suppliers.import','suppliers.table',
          'suppliers.table.createAccount','suppliers.table.deleteButton',
          'suppliers.table.editButton','suppliers.table.resetPassword',
          'suppliers.table.toggleStatus',
          'vehicles','vehicles.addButton','vehicles.downloadTemplate','vehicles.export',
          'vehicles.form','vehicles.form.brand','vehicles.form.color',
          'vehicles.form.luggageCapacity','vehicles.form.makeYear','vehicles.form.model',
          'vehicles.form.ownership','vehicles.form.plateNumber','vehicles.form.vehicleType',
          'vehicles.import','vehicles.table','vehicles.table.deleteButton',
          'vehicles.table.editButton','vehicles.table.toggleStatus',
          'vehicles.types','vehicles.types.addButton','vehicles.types.editButton',
        ],
      },
      {
        name: 'Viewer',
        slug: 'viewer',
        description: 'Read-only access to all modules',
        permissions: [
          'activity-logs','agents','customers','dashboard','dispatch','drivers',
          'finance','guest-bookings','job-locks','locations','public-prices',
          'reports','reps','suppliers','traffic-jobs','vehicles',
        ],
      },
    ];

    const skipPermissions = process.env.SKIP_PERMISSION_SEED === 'true';

    for (const roleData of systemRoles) {
      const role = await prisma.role.upsert({
        where: { slug: roleData.slug },
        update: { name: roleData.name, description: roleData.description },
        create: { name: roleData.name, slug: roleData.slug, description: roleData.description, isSystem: true },
      });
      console.log(`System role seeded: ${role.name} (${role.slug})`);

      // Assign admin users to admin role
      if (role.slug === 'admin') {
        await prisma.user.updateMany({
          where: { id: { in: [admin.id, superAdmin.id] } },
          data: { roleId: role.id },
        });
      }

      if (!skipPermissions && roleData.permissions.length > 0) {
        // Insert missing permissions; remove stale ones
        await prisma.rolePermissionV2.createMany({
          data: roleData.permissions.map((permissionKey) => ({ roleId: role.id, permissionKey })),
          skipDuplicates: true,
        });
        await prisma.rolePermissionV2.deleteMany({
          where: { roleId: role.id, permissionKey: { notIn: roleData.permissions } },
        });
        console.log(`  → Assigned ${roleData.permissions.length} permissions to ${role.name}`);
      }
    }

    if (skipPermissions) {
      console.log('System roles seeded (permission seeding skipped — SKIP_PERMISSION_SEED=true).');
    } else {
      console.log('System roles and permissions seeded.');
    }

    const skipSystemParams = process.env.SKIP_SYSTEM_PARAMS_SEED === 'true';

    if (skipSystemParams) {
      console.log('System parameters seeding skipped — SKIP_SYSTEM_PARAMS_SEED=true.');
    } else {
      // ─── SEED EGYPT LOCATIONS WITH COORDINATES ───
      await seedEgyptLocations(prisma);

      // Create sample vehicle types
      const sedanType = await prisma.vehicleType.upsert({
        where: { name: 'Sedan' },
        update: {},
        create: { name: 'Sedan', seatCapacity: 3 },
      });

      const minivanType = await prisma.vehicleType.upsert({
        where: { name: 'Minivan' },
        update: {},
        create: { name: 'Minivan', seatCapacity: 7 },
      });

      const coasterType = await prisma.vehicleType.upsert({
        where: { name: 'Coaster' },
        update: {},
        create: { name: 'Coaster', seatCapacity: 25 },
      });

      const busType = await prisma.vehicleType.upsert({
        where: { name: 'Bus' },
        update: {},
        create: { name: 'Bus', seatCapacity: 49 },
      });

      console.log(`Vehicle types seeded: ${sedanType.name}, ${minivanType.name}, ${coasterType.name}, ${busType.name}`);

      console.log('Agent price seeding skipped (removed from default seed).');
    }

    // ─── MANAGED EXTRAS CATALOG (seed the former hard-coded seat extras) ───
    for (const ex of [
      { name: 'Booster Seat', sortOrder: 1 },
      { name: 'Baby Seat', sortOrder: 2 },
      { name: 'Wheelchair', sortOrder: 3 },
    ]) {
      const existing = await prisma.b2cExtra.findFirst({ where: { name: ex.name } });
      if (!existing) {
        await prisma.b2cExtra.create({
          data: { name: ex.name, price: 0, currency: 'EGP', isActive: true, occupiesSeat: true, sortOrder: ex.sortOrder },
        });
        console.log(`Extra seeded: ${ex.name}`);
      } else if (!existing.occupiesSeat) {
        await prisma.b2cExtra.update({ where: { id: existing.id }, data: { occupiesSeat: true } });
      }
    }

    // ─── B2C WEBSITE AGENT (always seeded; selectable in online job form) ───
    // Bookings made on the public B2C site are attributed to this agent. Its display
    // name tracks the website's public name (WebsiteSettings.siteName), while the
    // isB2cWebsite flag is the stable key the convert flow uses to find it.
    const websiteSettings = await prisma.websiteSettings.findFirst({
      select: { siteName: true },
    });
    const siteName = websiteSettings?.siteName?.trim() || 'iTour Transfers';

    // Find by stable marker first; fall back to the original seeded name for first run.
    const existingB2cAgent =
      (await prisma.agent.findFirst({
        where: { isB2cWebsite: true, deletedAt: null },
      })) ??
      (await prisma.agent.findFirst({
        where: { legalName: 'B2C Website', deletedAt: null },
      }));

    if (!existingB2cAgent) {
      const b2cAgent = await prisma.agent.create({
        data: {
          legalName: siteName,
          tradeName: siteName,
          isActive: true,
          isB2cWebsite: true,
        },
      });
      console.log(`Website agent created: ${b2cAgent.id} (${siteName})`);
    } else {
      await prisma.agent.update({
        where: { id: existingB2cAgent.id },
        data: { legalName: siteName, tradeName: siteName, isB2cWebsite: true },
      });
      console.log(`Website agent updated to site name: ${siteName}`);
    }

    // CMS static pages for the B2C site (created as drafts until edited).
    const staticPages = [
      { slug: 'terms-and-conditions', title: 'Terms & Conditions' },
      { slug: 'privacy-policy', title: 'Privacy Policy' },
      { slug: 'about-us', title: 'About Us' },
    ];
    for (const page of staticPages) {
      await prisma.staticPage.upsert({
        where: { slug: page.slug },
        update: {},
        create: { slug: page.slug, title: page.title, isPublished: false },
      });
    }
    console.log(`Static pages seeded: ${staticPages.map((p) => p.slug).join(', ')}`);

    // Backfill B2C invoices for already-paid guest bookings (idempotent — only
    // creates invoices for paid bookings that don't have one yet).
    const paidWithoutInvoice = await prisma.guestBooking.findMany({
      where: { paymentStatus: 'PAID', invoice: { is: null } },
      select: {
        id: true, b2cClientId: true, subtotal: true,
        taxAmount: true, total: true, currency: true,
      },
      orderBy: { createdAt: 'asc' },
    });
    if (paidWithoutInvoice.length > 0) {
      const rows: { invoice_number: string }[] = await prisma.$queryRawUnsafe(
        `SELECT invoice_number FROM b2c_invoices WHERE invoice_number ~ '^INV-B2C-[0-9]+$' ORDER BY invoice_number DESC LIMIT 1`,
      );
      let next = 1;
      if (rows.length > 0) {
        const seq = parseInt(rows[0].invoice_number.split('-')[2], 10);
        if (!isNaN(seq)) next = seq + 1;
      }
      for (const b of paidWithoutInvoice) {
        await prisma.b2CInvoice.create({
          data: {
            invoiceNumber: `INV-B2C-${String(next).padStart(5, '0')}`,
            guestBookingId: b.id,
            b2cClientId: b.b2cClientId,
            subtotal: b.subtotal,
            taxAmount: b.taxAmount,
            total: b.total,
            currency: b.currency,
            status: 'PAID',
          },
        });
        next++;
      }
      console.log(`B2C invoices backfilled: ${paidWithoutInvoice.length}`);
    } else {
      console.log('B2C invoices backfill: none needed');
    }

    console.log('\nSeed completed successfully.');
  } finally {
    await prisma.$disconnect();
    await pool.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
