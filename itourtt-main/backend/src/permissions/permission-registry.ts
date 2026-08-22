// ─────────────────────────────────────────────
// PERMISSION REGISTRY – Single Source of Truth
// ─────────────────────────────────────────────
// This file defines ALL available permission keys as a tree.
// The tree structure is used by the admin UI; the flat keys
// are stored in the database.
// Keep this file in sync with frontend/src/lib/permission-registry.ts

export interface PermissionNode {
  key: string;
  labelKey: string;
  children?: PermissionNode[];
}

export const PERMISSION_REGISTRY: PermissionNode[] = [
  // ─── DASHBOARD ───
  {
    key: 'dashboard',
    labelKey: 'permissions.dashboard',
    children: [
      { key: 'dashboard.stats', labelKey: 'permissions.dashboard.stats' },
      { key: 'dashboard.recentJobs', labelKey: 'permissions.dashboard.recentJobs' },
      { key: 'dashboard.revenue', labelKey: 'permissions.dashboard.revenue' },
    ],
  },

  // ─── DISPATCH ───
  {
    key: 'dispatch',
    labelKey: 'permissions.dispatch',
    children: [
      { key: 'dispatch.grid', labelKey: 'permissions.dispatch.grid' },
      { key: 'dispatch.datePicker', labelKey: 'permissions.dispatch.datePicker' },
      {
        key: 'dispatch.assignment',
        labelKey: 'permissions.dispatch.assignment',
        children: [
          { key: 'dispatch.assignment.assignVehicle', labelKey: 'permissions.dispatch.assignment.assignVehicle' },
          { key: 'dispatch.assignment.assignDriver', labelKey: 'permissions.dispatch.assignment.assignDriver' },
          { key: 'dispatch.assignment.assignRep', labelKey: 'permissions.dispatch.assignment.assignRep' },
          { key: 'dispatch.assignment.unassign', labelKey: 'permissions.dispatch.assignment.unassign' },
          { key: 'dispatch.assignment.changeStatus', labelKey: 'permissions.dispatch.assignment.changeStatus' },
          { key: 'dispatch.assignment.unlock48h', labelKey: 'permissions.dispatch.assignment.unlock48h' },
        ],
      },
      { key: 'dispatch.exportButton', labelKey: 'permissions.dispatch.exportButton' },
    ],
  },

  // ─── TRAFFIC JOBS ───
  {
    key: 'traffic-jobs',
    labelKey: 'permissions.trafficJobs',
    children: [
      // Online jobs
      {
        key: 'traffic-jobs.online',
        labelKey: 'permissions.trafficJobs.online',
        children: [
          { key: 'traffic-jobs.online.createJob', labelKey: 'permissions.trafficJobs.online.createJob' },
          {
            key: 'traffic-jobs.online.form',
            labelKey: 'permissions.trafficJobs.online.form',
            children: [
              { key: 'traffic-jobs.online.form.provider', labelKey: 'permissions.trafficJobs.online.form.provider' },
              { key: 'traffic-jobs.online.form.agentRef', labelKey: 'permissions.trafficJobs.online.form.agentRef' },
              { key: 'traffic-jobs.online.form.serviceType', labelKey: 'permissions.trafficJobs.online.form.serviceType' },
              { key: 'traffic-jobs.online.form.dateTime', labelKey: 'permissions.trafficJobs.online.form.dateTime' },
              { key: 'traffic-jobs.online.form.clientInfo', labelKey: 'permissions.trafficJobs.online.form.clientInfo' },
              { key: 'traffic-jobs.online.form.paxCount', labelKey: 'permissions.trafficJobs.online.form.paxCount' },
              { key: 'traffic-jobs.online.form.route', labelKey: 'permissions.trafficJobs.online.form.route' },
              { key: 'traffic-jobs.online.form.flightInfo', labelKey: 'permissions.trafficJobs.online.form.flightInfo' },
              { key: 'traffic-jobs.online.form.extras', labelKey: 'permissions.trafficJobs.online.form.extras' },
              { key: 'traffic-jobs.online.form.requestedVehicleType', labelKey: 'permissions.trafficJobs.online.form.requestedVehicleType' },
              { key: 'traffic-jobs.online.form.notes', labelKey: 'permissions.trafficJobs.online.form.notes' },
              { key: 'traffic-jobs.online.form.printSign', labelKey: 'permissions.trafficJobs.online.form.printSign' },
            ],
          },
          {
            key: 'traffic-jobs.online.table',
            labelKey: 'permissions.trafficJobs.online.table',
            children: [
              { key: 'traffic-jobs.online.table.statusFilter', labelKey: 'permissions.trafficJobs.online.table.statusFilter' },
            ],
          },
        ],
      },
      // B2B jobs
      {
        key: 'traffic-jobs.b2b',
        labelKey: 'permissions.trafficJobs.b2b',
        children: [
          { key: 'traffic-jobs.b2b.createJob', labelKey: 'permissions.trafficJobs.b2b.createJob' },
          {
            key: 'traffic-jobs.b2b.form',
            labelKey: 'permissions.trafficJobs.b2b.form',
            children: [
              { key: 'traffic-jobs.b2b.form.customer', labelKey: 'permissions.trafficJobs.b2b.form.customer' },
              { key: 'traffic-jobs.b2b.form.serviceType', labelKey: 'permissions.trafficJobs.b2b.form.serviceType' },
              { key: 'traffic-jobs.b2b.form.dateTime', labelKey: 'permissions.trafficJobs.b2b.form.dateTime' },
              { key: 'traffic-jobs.b2b.form.paxCount', labelKey: 'permissions.trafficJobs.b2b.form.paxCount' },
              { key: 'traffic-jobs.b2b.form.route', labelKey: 'permissions.trafficJobs.b2b.form.route' },
              { key: 'traffic-jobs.b2b.form.flightInfo', labelKey: 'permissions.trafficJobs.b2b.form.flightInfo' },
              { key: 'traffic-jobs.b2b.form.meetingInfo', labelKey: 'permissions.trafficJobs.b2b.form.meetingInfo' },
              { key: 'traffic-jobs.b2b.form.notes', labelKey: 'permissions.trafficJobs.b2b.form.notes' },
            ],
          },
          {
            key: 'traffic-jobs.b2b.table',
            labelKey: 'permissions.trafficJobs.b2b.table',
            children: [
              { key: 'traffic-jobs.b2b.table.statusFilter', labelKey: 'permissions.trafficJobs.b2b.table.statusFilter' },
            ],
          },
          { key: 'traffic-jobs.b2b.importJobs', labelKey: 'permissions.trafficJobs.b2b.importJobs' },
        ],
      },
    ],
  },

  // ─── AGENTS ───
  {
    key: 'agents',
    labelKey: 'permissions.agents',
    children: [
      { key: 'agents.addButton', labelKey: 'permissions.agents.addButton' },
      {
        key: 'agents.table',
        labelKey: 'permissions.agents.table',
        children: [
          { key: 'agents.table.editButton', labelKey: 'permissions.agents.table.editButton' },
          { key: 'agents.table.deleteButton', labelKey: 'permissions.agents.table.deleteButton' },
          { key: 'agents.table.toggleStatus', labelKey: 'permissions.agents.table.toggleStatus' },
        ],
      },
      { key: 'agents.export', labelKey: 'permissions.agents.export' },
      { key: 'agents.downloadTemplate', labelKey: 'permissions.agents.downloadTemplate' },
      { key: 'agents.import', labelKey: 'permissions.agents.import' },
      {
        key: 'agents.form',
        labelKey: 'permissions.agents.form',
        children: [
          { key: 'agents.form.legalName', labelKey: 'permissions.agents.form.legalName' },
          { key: 'agents.form.tradeName', labelKey: 'permissions.agents.form.tradeName' },
          { key: 'agents.form.taxId', labelKey: 'permissions.agents.form.taxId' },
          { key: 'agents.form.contactInfo', labelKey: 'permissions.agents.form.contactInfo' },
          { key: 'agents.form.currency', labelKey: 'permissions.agents.form.currency' },
          { key: 'agents.form.refPattern', labelKey: 'permissions.agents.form.refPattern' },
          { key: 'agents.form.creditLimit', labelKey: 'permissions.agents.form.creditLimit' },
          { key: 'agents.form.creditDays', labelKey: 'permissions.agents.form.creditDays' },
        ],
      },
    ],
  },

  // ─── CUSTOMERS ───
  {
    key: 'customers',
    labelKey: 'permissions.customers',
    children: [
      { key: 'customers.addButton', labelKey: 'permissions.customers.addButton' },
      {
        key: 'customers.table',
        labelKey: 'permissions.customers.table',
        children: [
          { key: 'customers.table.editButton', labelKey: 'permissions.customers.table.editButton' },
          { key: 'customers.table.deleteButton', labelKey: 'permissions.customers.table.deleteButton' },
          { key: 'customers.table.viewButton', labelKey: 'permissions.customers.table.viewButton' },
          { key: 'customers.table.toggleStatus', labelKey: 'permissions.customers.table.toggleStatus' },
        ],
      },
      { key: 'customers.export', labelKey: 'permissions.customers.export' },
      { key: 'customers.downloadTemplate', labelKey: 'permissions.customers.downloadTemplate' },
      { key: 'customers.import', labelKey: 'permissions.customers.import' },
      {
        key: 'customers.form',
        labelKey: 'permissions.customers.form',
        children: [
          { key: 'customers.form.legalName', labelKey: 'permissions.customers.form.legalName' },
          { key: 'customers.form.tradeName', labelKey: 'permissions.customers.form.tradeName' },
          { key: 'customers.form.taxId', labelKey: 'permissions.customers.form.taxId' },
          { key: 'customers.form.contactInfo', labelKey: 'permissions.customers.form.contactInfo' },
          { key: 'customers.form.currency', labelKey: 'permissions.customers.form.currency' },
          { key: 'customers.form.creditLimit', labelKey: 'permissions.customers.form.creditLimit' },
          { key: 'customers.form.creditDays', labelKey: 'permissions.customers.form.creditDays' },
        ],
      },
      {
        key: 'customers.detail',
        labelKey: 'permissions.customers.detail',
        children: [
          {
            key: 'customers.detail.priceList',
            labelKey: 'permissions.customers.detail.priceList',
            children: [
              { key: 'customers.detail.priceList.addRoute', labelKey: 'permissions.customers.detail.priceList.addRoute' },
              { key: 'customers.detail.priceList.editPrice', labelKey: 'permissions.customers.detail.priceList.editPrice' },
              { key: 'customers.detail.priceList.deleteRoute', labelKey: 'permissions.customers.detail.priceList.deleteRoute' },
              { key: 'customers.detail.priceList.import', labelKey: 'permissions.customers.detail.priceList.import' },
              { key: 'customers.detail.priceList.downloadTemplate', labelKey: 'permissions.customers.detail.priceList.downloadTemplate' },
              { key: 'customers.detail.priceList.saveAll', labelKey: 'permissions.customers.detail.priceList.saveAll' },
            ],
          },
          {
            key: 'customers.detail.importTemplates',
            labelKey: 'permissions.customers.detail.importTemplates',
            children: [
              { key: 'customers.detail.importTemplates.upload', labelKey: 'permissions.customers.detail.importTemplates.upload' },
              { key: 'customers.detail.importTemplates.delete', labelKey: 'permissions.customers.detail.importTemplates.delete' },
            ],
          },
        ],
      },
    ],
  },

  // ─── FINANCE ───
  {
    key: 'finance',
    labelKey: 'permissions.finance',
    children: [
      {
        key: 'finance.invoices',
        labelKey: 'permissions.finance.invoices',
        children: [
          { key: 'finance.invoices.addButton', labelKey: 'permissions.finance.invoices.addButton' },
          {
            key: 'finance.invoices.detail',
            labelKey: 'permissions.finance.invoices.detail',
            children: [
              { key: 'finance.invoices.detail.editLines', labelKey: 'permissions.finance.invoices.detail.editLines' },
              { key: 'finance.invoices.detail.addLine', labelKey: 'permissions.finance.invoices.detail.addLine' },
              { key: 'finance.invoices.detail.deleteLine', labelKey: 'permissions.finance.invoices.detail.deleteLine' },
              { key: 'finance.invoices.detail.postButton', labelKey: 'permissions.finance.invoices.detail.postButton' },
              { key: 'finance.invoices.detail.cancelButton', labelKey: 'permissions.finance.invoices.detail.cancelButton' },
              { key: 'finance.invoices.detail.applyVat', labelKey: 'permissions.finance.invoices.detail.applyVat' },
            ],
          },
          { key: 'finance.invoices.recordPayment', labelKey: 'permissions.finance.invoices.recordPayment' },
        ],
      },
      { key: 'finance.b2cInvoices', labelKey: 'permissions.finance.b2cInvoices' },
      {
        key: 'finance.payments',
        labelKey: 'permissions.finance.payments',
        children: [
          { key: 'finance.payments.addButton', labelKey: 'permissions.finance.payments.addButton' },
          { key: 'finance.payments.deleteButton', labelKey: 'permissions.finance.payments.deleteButton' },
        ],
      },
      {
        key: 'finance.exports',
        labelKey: 'permissions.finance.exports',
        children: [
          { key: 'finance.exports.customers', labelKey: 'permissions.finance.exports.customers' },
          { key: 'finance.exports.suppliers', labelKey: 'permissions.finance.exports.suppliers' },
          { key: 'finance.exports.invoices', labelKey: 'permissions.finance.exports.invoices' },
          { key: 'finance.exports.vendorBills', labelKey: 'permissions.finance.exports.vendorBills' },
          { key: 'finance.exports.payments', labelKey: 'permissions.finance.exports.payments' },
          { key: 'finance.exports.journals', labelKey: 'permissions.finance.exports.journals' },
          { key: 'finance.exports.collections', labelKey: 'permissions.finance.exports.collections' },
          { key: 'finance.odooExport', labelKey: 'permissions.finance.odooExport' },
        ],
      },
    ],
  },

  // ─── REPORTS ───
  {
    key: 'reports',
    labelKey: 'permissions.reports',
    children: [
      { key: 'reports.dailyDispatch', labelKey: 'permissions.reports.dailyDispatch' },
      { key: 'reports.driverTrips', labelKey: 'permissions.reports.driverTrips' },
      { key: 'reports.driverScore', labelKey: 'permissions.reports.driverScore' },
      { key: 'reports.agentStatement', labelKey: 'permissions.reports.agentStatement' },
      { key: 'reports.repFees', labelKey: 'permissions.reports.repFees' },
      { key: 'reports.repScore', labelKey: 'permissions.reports.repScore' },
      { key: 'reports.guestSurveys', labelKey: 'permissions.reports.guestSurveys' },
      { key: 'reports.revenue', labelKey: 'permissions.reports.revenue' },
      { key: 'reports.vehicleCompliance', labelKey: 'permissions.reports.vehicleCompliance' },
      { key: 'reports.jobStatus', labelKey: 'permissions.reports.jobStatus' },
      { key: 'reports.evidence', labelKey: 'permissions.reports.evidence' },
      { key: 'reports.supplierJobs', labelKey: 'permissions.reports.supplierJobs' },
      { key: 'reports.carJobs', labelKey: 'permissions.reports.carJobs' },
      { key: 'reports.visa', labelKey: 'permissions.reports.visa' },
      { key: 'reports.sales', labelKey: 'permissions.reports.sales' },
      { key: 'reports.departure', labelKey: 'permissions.reports.departure' },
      { key: 'reports.flightDelay', labelKey: 'permissions.reports.flightDelay' },
      { key: 'reports.review', labelKey: 'permissions.reports.review' },
    ],
  },

  // ─── VEHICLES ───
  {
    key: 'vehicles',
    labelKey: 'permissions.vehicles',
    children: [
      {
        key: 'vehicles.types',
        labelKey: 'permissions.vehicles.types',
        children: [
          { key: 'vehicles.types.addButton', labelKey: 'permissions.vehicles.types.addButton' },
          { key: 'vehicles.types.editButton', labelKey: 'permissions.vehicles.types.editButton' },
        ],
      },
      { key: 'vehicles.addButton', labelKey: 'permissions.vehicles.addButton' },
      {
        key: 'vehicles.table',
        labelKey: 'permissions.vehicles.table',
        children: [
          { key: 'vehicles.table.editButton', labelKey: 'permissions.vehicles.table.editButton' },
          { key: 'vehicles.table.deleteButton', labelKey: 'permissions.vehicles.table.deleteButton' },
          { key: 'vehicles.table.toggleStatus', labelKey: 'permissions.vehicles.table.toggleStatus' },
        ],
      },
      { key: 'vehicles.import', labelKey: 'permissions.vehicles.import' },
      { key: 'vehicles.export', labelKey: 'permissions.vehicles.export' },
      { key: 'vehicles.downloadTemplate', labelKey: 'permissions.vehicles.downloadTemplate' },
      {
        key: 'vehicles.form',
        labelKey: 'permissions.vehicles.form',
        children: [
          { key: 'vehicles.form.plateNumber', labelKey: 'permissions.vehicles.form.plateNumber' },
          { key: 'vehicles.form.vehicleType', labelKey: 'permissions.vehicles.form.vehicleType' },
          { key: 'vehicles.form.color', labelKey: 'permissions.vehicles.form.color' },
          { key: 'vehicles.form.brand', labelKey: 'permissions.vehicles.form.brand' },
          { key: 'vehicles.form.model', labelKey: 'permissions.vehicles.form.model' },
          { key: 'vehicles.form.makeYear', labelKey: 'permissions.vehicles.form.makeYear' },
          { key: 'vehicles.form.luggageCapacity', labelKey: 'permissions.vehicles.form.luggageCapacity' },
          { key: 'vehicles.form.ownership', labelKey: 'permissions.vehicles.form.ownership' },
        ],
      },
    ],
  },

  // ─── DRIVERS ───
  {
    key: 'drivers',
    labelKey: 'permissions.drivers',
    children: [
      { key: 'drivers.addButton', labelKey: 'permissions.drivers.addButton' },
      {
        key: 'drivers.table',
        labelKey: 'permissions.drivers.table',
        children: [
          { key: 'drivers.table.editButton', labelKey: 'permissions.drivers.table.editButton' },
          { key: 'drivers.table.deleteButton', labelKey: 'permissions.drivers.table.deleteButton' },
          { key: 'drivers.table.toggleStatus', labelKey: 'permissions.drivers.table.toggleStatus' },
          { key: 'drivers.table.uploadAttachment', labelKey: 'permissions.drivers.table.uploadAttachment' },
          { key: 'drivers.table.createAccount', labelKey: 'permissions.drivers.table.createAccount' },
          { key: 'drivers.table.resetPassword', labelKey: 'permissions.drivers.table.resetPassword' },
        ],
      },
      { key: 'drivers.import', labelKey: 'permissions.drivers.import' },
      { key: 'drivers.export', labelKey: 'permissions.drivers.export' },
      { key: 'drivers.downloadTemplate', labelKey: 'permissions.drivers.downloadTemplate' },
      {
        key: 'drivers.form',
        labelKey: 'permissions.drivers.form',
        children: [
          { key: 'drivers.form.name', labelKey: 'permissions.drivers.form.name' },
          { key: 'drivers.form.mobile', labelKey: 'permissions.drivers.form.mobile' },
          { key: 'drivers.form.licenseNumber', labelKey: 'permissions.drivers.form.licenseNumber' },
          { key: 'drivers.form.licenseExpiry', labelKey: 'permissions.drivers.form.licenseExpiry' },
        ],
      },
    ],
  },

  // ─── REPS ───
  {
    key: 'reps',
    labelKey: 'permissions.reps',
    children: [
      { key: 'reps.addButton', labelKey: 'permissions.reps.addButton' },
      {
        key: 'reps.table',
        labelKey: 'permissions.reps.table',
        children: [
          { key: 'reps.table.editButton', labelKey: 'permissions.reps.table.editButton' },
          { key: 'reps.table.deleteButton', labelKey: 'permissions.reps.table.deleteButton' },
          { key: 'reps.table.toggleStatus', labelKey: 'permissions.reps.table.toggleStatus' },
          { key: 'reps.table.uploadAttachment', labelKey: 'permissions.reps.table.uploadAttachment' },
          { key: 'reps.table.createAccount', labelKey: 'permissions.reps.table.createAccount' },
          { key: 'reps.table.resetPassword', labelKey: 'permissions.reps.table.resetPassword' },
        ],
      },
      { key: 'reps.import', labelKey: 'permissions.reps.import' },
      { key: 'reps.export', labelKey: 'permissions.reps.export' },
      { key: 'reps.downloadTemplate', labelKey: 'permissions.reps.downloadTemplate' },
      {
        key: 'reps.form',
        labelKey: 'permissions.reps.form',
        children: [
          { key: 'reps.form.name', labelKey: 'permissions.reps.form.name' },
          { key: 'reps.form.mobile', labelKey: 'permissions.reps.form.mobile' },
          { key: 'reps.form.feePerFlight', labelKey: 'permissions.reps.form.feePerFlight' },
        ],
      },
    ],
  },

  // ─── SUPPLIERS ───
  {
    key: 'suppliers',
    labelKey: 'permissions.suppliers',
    children: [
      { key: 'suppliers.addButton', labelKey: 'permissions.suppliers.addButton' },
      {
        key: 'suppliers.table',
        labelKey: 'permissions.suppliers.table',
        children: [
          { key: 'suppliers.table.editButton', labelKey: 'permissions.suppliers.table.editButton' },
          { key: 'suppliers.table.deleteButton', labelKey: 'permissions.suppliers.table.deleteButton' },
          { key: 'suppliers.table.toggleStatus', labelKey: 'permissions.suppliers.table.toggleStatus' },
          { key: 'suppliers.table.createAccount', labelKey: 'permissions.suppliers.table.createAccount' },
          { key: 'suppliers.table.resetPassword', labelKey: 'permissions.suppliers.table.resetPassword' },
        ],
      },
      { key: 'suppliers.export', labelKey: 'permissions.suppliers.export' },
      { key: 'suppliers.downloadTemplate', labelKey: 'permissions.suppliers.downloadTemplate' },
      { key: 'suppliers.import', labelKey: 'permissions.suppliers.import' },
      {
        key: 'suppliers.form',
        labelKey: 'permissions.suppliers.form',
        children: [
          { key: 'suppliers.form.legalName', labelKey: 'permissions.suppliers.form.legalName' },
          { key: 'suppliers.form.tradeName', labelKey: 'permissions.suppliers.form.tradeName' },
          { key: 'suppliers.form.taxId', labelKey: 'permissions.suppliers.form.taxId' },
          { key: 'suppliers.form.contactInfo', labelKey: 'permissions.suppliers.form.contactInfo' },
        ],
      },
    ],
  },

  // ─── LOCATIONS ───
  {
    key: 'locations',
    labelKey: 'permissions.locations',
    children: [
      {
        key: 'locations.countries',
        labelKey: 'permissions.locations.countries',
        children: [
          { key: 'locations.countries.addButton', labelKey: 'permissions.locations.countries.addButton' },
          { key: 'locations.countries.editButton', labelKey: 'permissions.locations.countries.editButton' },
        ],
      },
      {
        key: 'locations.airports',
        labelKey: 'permissions.locations.airports',
        children: [
          { key: 'locations.airports.addButton', labelKey: 'permissions.locations.airports.addButton' },
          { key: 'locations.airports.editButton', labelKey: 'permissions.locations.airports.editButton' },
          { key: 'locations.airports.deleteButton', labelKey: 'permissions.locations.airports.deleteButton' },
        ],
      },
      {
        key: 'locations.cities',
        labelKey: 'permissions.locations.cities',
        children: [
          { key: 'locations.cities.addButton', labelKey: 'permissions.locations.cities.addButton' },
          { key: 'locations.cities.editButton', labelKey: 'permissions.locations.cities.editButton' },
          { key: 'locations.cities.deleteButton', labelKey: 'permissions.locations.cities.deleteButton' },
        ],
      },
      {
        key: 'locations.zones',
        labelKey: 'permissions.locations.zones',
        children: [
          { key: 'locations.zones.addButton', labelKey: 'permissions.locations.zones.addButton' },
          { key: 'locations.zones.editButton', labelKey: 'permissions.locations.zones.editButton' },
          { key: 'locations.zones.deleteButton', labelKey: 'permissions.locations.zones.deleteButton' },
        ],
      },
      {
        key: 'locations.hotels',
        labelKey: 'permissions.locations.hotels',
        children: [
          { key: 'locations.hotels.addButton', labelKey: 'permissions.locations.hotels.addButton' },
          { key: 'locations.hotels.editButton', labelKey: 'permissions.locations.hotels.editButton' },
          { key: 'locations.hotels.deleteButton', labelKey: 'permissions.locations.hotels.deleteButton' },
        ],
      },
      { key: 'locations.export', labelKey: 'permissions.locations.export' },
      { key: 'locations.downloadTemplate', labelKey: 'permissions.locations.downloadTemplate' },
      { key: 'locations.import', labelKey: 'permissions.locations.import' },
    ],
  },

  // ─── COMPANY SETTINGS ───
  {
    key: 'company',
    labelKey: 'permissions.company',
    children: [
      { key: 'company.editSettings', labelKey: 'permissions.company.editSettings' },
      { key: 'company.uploadLogo', labelKey: 'permissions.company.uploadLogo' },
      { key: 'company.uploadFavicon', labelKey: 'permissions.company.uploadFavicon' },
    ],
  },

  // ─── USERS & ROLES ───
  {
    key: 'users',
    labelKey: 'permissions.users',
    children: [
      { key: 'users.addButton', labelKey: 'permissions.users.addButton' },
      {
        key: 'users.table',
        labelKey: 'permissions.users.table',
        children: [
          { key: 'users.table.editButton', labelKey: 'permissions.users.table.editButton' },
          { key: 'users.table.changeRole', labelKey: 'permissions.users.table.changeRole' },
          { key: 'users.table.deactivate', labelKey: 'permissions.users.table.deactivate' },
        ],
      },
      {
        key: 'users.roles',
        labelKey: 'permissions.users.roles',
        children: [
          { key: 'users.roles.addButton', labelKey: 'permissions.users.roles.addButton' },
          { key: 'users.roles.editButton', labelKey: 'permissions.users.roles.editButton' },
          { key: 'users.roles.deleteButton', labelKey: 'permissions.users.roles.deleteButton' },
          { key: 'users.roles.editPermissions', labelKey: 'permissions.users.roles.editPermissions' },
        ],
      },
    ],
  },

  // ─── GUEST BOOKINGS (B2C) ───
  {
    key: 'guest-bookings',
    labelKey: 'permissions.guestBookings',
    children: [
      { key: 'guest-bookings.convert', labelKey: 'permissions.guestBookings.convert' },
      { key: 'guest-bookings.cancel', labelKey: 'permissions.guestBookings.cancel' },
    ],
  },

  // ─── PUBLIC PRICES (B2C) ───
  {
    key: 'public-prices',
    labelKey: 'permissions.publicPrices',
    children: [
      { key: 'public-prices.bulk', labelKey: 'permissions.publicPrices.bulk' },
      { key: 'public-prices.delete', labelKey: 'permissions.publicPrices.delete' },
    ],
  },

  // ─── B2C EXTRAS ───
  {
    key: 'extras',
    labelKey: 'permissions.extras',
    children: [
      { key: 'extras.addButton', labelKey: 'permissions.extras.addButton' },
      { key: 'extras.editButton', labelKey: 'permissions.extras.editButton' },
      { key: 'extras.deleteButton', labelKey: 'permissions.extras.deleteButton' },
    ],
  },

  // ─── DRIVER TARIFFS ───
  {
    key: 'driver-tariffs',
    labelKey: 'permissions.driverTariffs',
    children: [
      { key: 'driver-tariffs.upsert', labelKey: 'permissions.driverTariffs.upsert' },
      { key: 'driver-tariffs.delete', labelKey: 'permissions.driverTariffs.delete' },
    ],
  },

  // ─── JOB CONTROL (admin bulk job tools; granted per-user via the matrix) ───
  {
    key: 'job-control',
    labelKey: 'permissions.jobControl',
  },

  // ─── JOB LOCKS ───
  {
    key: 'job-locks',
    labelKey: 'permissions.jobLocks',
    children: [
      { key: 'job-locks.dispatcher', labelKey: 'permissions.jobLocks.dispatcher' },
      { key: 'job-locks.driver', labelKey: 'permissions.jobLocks.driver' },
      { key: 'job-locks.rep', labelKey: 'permissions.jobLocks.rep' },
      { key: 'job-locks.supplier', labelKey: 'permissions.jobLocks.supplier' },
      { key: 'job-locks.edit', labelKey: 'permissions.jobLocks.edit' },
      { key: 'job-locks.b2c', labelKey: 'permissions.jobLocks.b2c' },
      { key: 'job-locks.online', labelKey: 'permissions.jobLocks.online' },
    ],
  },

  // ─── ACTIVITY LOGS ───
  {
    key: 'activity-logs',
    labelKey: 'permissions.activityLogs',
    children: [
      { key: 'activity-logs.export', labelKey: 'permissions.activityLogs.export' },
    ],
  },

  // ─── WHATSAPP NOTIFICATIONS ───
  {
    key: 'whatsapp',
    labelKey: 'permissions.whatsapp',
    children: [
      {
        key: 'whatsapp.settings',
        labelKey: 'permissions.whatsapp.settings',
        children: [
          { key: 'whatsapp.settings.editSettings', labelKey: 'permissions.whatsapp.settings.editSettings' },
        ],
      },
      { key: 'whatsapp.logs', labelKey: 'permissions.whatsapp.logs' },
      { key: 'whatsapp.testSend', labelKey: 'permissions.whatsapp.testSend' },
      { key: 'whatsapp.uploadMedia', labelKey: 'permissions.whatsapp.uploadMedia' },
    ],
  },

  // ─── B2C WEBSITE CONTENT ───
  {
    key: 'website-content',
    labelKey: 'permissions.websiteContent',
    children: [
      { key: 'website-content.cityPages', labelKey: 'permissions.websiteContent.cityPages' },
      { key: 'website-content.blog', labelKey: 'permissions.websiteContent.blog' },
      { key: 'website-content.pageSeo', labelKey: 'permissions.websiteContent.pageSeo' },
      { key: 'website-content.pages', labelKey: 'permissions.websiteContent.pages' },
    ],
  },

  // ─── CONTACT MESSAGES (B2C inbound) ───
  {
    key: 'contact-messages',
    labelKey: 'permissions.contactMessages',
  },
];

/**
 * Flatten the registry tree into a list of all permission keys.
 */
export function getAllPermissionKeys(
  nodes: PermissionNode[] = PERMISSION_REGISTRY,
): string[] {
  const keys: string[] = [];
  for (const node of nodes) {
    keys.push(node.key);
    if (node.children) {
      keys.push(...getAllPermissionKeys(node.children));
    }
  }
  return keys;
}

/**
 * Check if a key exists in the registry.
 */
export function isValidPermissionKey(key: string): boolean {
  return getAllPermissionKeys().includes(key);
}

/**
 * Get all ancestor keys for a given permission key.
 * E.g. "agents.table.editButton" → ["agents", "agents.table"]
 */
export function getAncestorKeys(key: string): string[] {
  const parts = key.split('.');
  const ancestors: string[] = [];
  for (let i = 1; i < parts.length; i++) {
    ancestors.push(parts.slice(0, i).join('.'));
  }
  return ancestors;
}

/**
 * Get all descendant keys for a given key from the registry.
 */
export function getDescendantKeys(
  parentKey: string,
  nodes: PermissionNode[] = PERMISSION_REGISTRY,
): string[] {
  const keys: string[] = [];

  function findAndCollect(
    searchKey: string,
    currentNodes: PermissionNode[],
  ): boolean {
    for (const node of currentNodes) {
      if (node.key === searchKey) {
        // Found the parent, collect all its descendants
        if (node.children) {
          collectAll(node.children);
        }
        return true;
      }
      if (node.children && findAndCollect(searchKey, node.children)) {
        return true;
      }
    }
    return false;
  }

  function collectAll(currentNodes: PermissionNode[]): void {
    for (const node of currentNodes) {
      keys.push(node.key);
      if (node.children) {
        collectAll(node.children);
      }
    }
  }

  findAndCollect(parentKey, nodes);
  return keys;
}
