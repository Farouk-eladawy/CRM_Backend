// ─────────────────────────────────────────────
// PERMISSION REGISTRY – Single Source of Truth
// ─────────────────────────────────────────────
// This file defines ALL available permission keys as a tree.
// The tree structure is used by the admin UI; the flat keys
// are stored in the database.
// Keep this file in sync with backend/src/permissions/permission-registry.ts

export type CrudType =
  | 'page'     // top-level section key — master toggle
  | 'section'  // intermediate grouping node
  | 'C'        // Create
  | 'R'        // Read / View
  | 'U'        // Update / Edit
  | 'D'        // Delete
  | 'export'   // Export / Download template
  | 'import'   // Import
  | 'field'    // Form field-level key
  | 'action';  // Special action (unlock, reset password, etc.)

export interface PermissionNode {
  key: string;
  labelKey: string;
  crudType?: CrudType;
  children?: PermissionNode[];
}

export const PERMISSION_REGISTRY: PermissionNode[] = [
  // ─── DASHBOARD ───
  {
    key: 'dashboard',
    labelKey: 'permissions.dashboard',
    crudType: 'page',
    children: [
      { key: 'dashboard.stats',      labelKey: 'permissions.dashboard.stats',      crudType: 'R' },
      { key: 'dashboard.recentJobs', labelKey: 'permissions.dashboard.recentJobs', crudType: 'R' },
      { key: 'dashboard.revenue',    labelKey: 'permissions.dashboard.revenue',    crudType: 'R' },
    ],
  },

  // ─── DISPATCH ───
  {
    key: 'dispatch',
    labelKey: 'permissions.dispatch',
    crudType: 'page',
    children: [
      { key: 'dispatch.grid',       labelKey: 'permissions.dispatch.grid',       crudType: 'R' },
      { key: 'dispatch.datePicker', labelKey: 'permissions.dispatch.datePicker', crudType: 'R' },
      {
        key: 'dispatch.assignment',
        labelKey: 'permissions.dispatch.assignment',
        crudType: 'section',
        children: [
          { key: 'dispatch.assignment.assignVehicle',  labelKey: 'permissions.dispatch.assignment.assignVehicle',  crudType: 'U' },
          { key: 'dispatch.assignment.assignDriver',   labelKey: 'permissions.dispatch.assignment.assignDriver',   crudType: 'U' },
          { key: 'dispatch.assignment.assignRep',      labelKey: 'permissions.dispatch.assignment.assignRep',      crudType: 'U' },
          { key: 'dispatch.assignment.unassign',       labelKey: 'permissions.dispatch.assignment.unassign',       crudType: 'action' },
          { key: 'dispatch.assignment.changeStatus',   labelKey: 'permissions.dispatch.assignment.changeStatus',   crudType: 'U' },
          { key: 'dispatch.assignment.unlock48h',      labelKey: 'permissions.dispatch.assignment.unlock48h',      crudType: 'action' },
        ],
      },
      { key: 'dispatch.exportButton', labelKey: 'permissions.dispatch.exportButton', crudType: 'export' },
    ],
  },

  // ─── TRAFFIC JOBS ───
  {
    key: 'traffic-jobs',
    labelKey: 'permissions.trafficJobs',
    crudType: 'page',
    children: [
      // Online jobs
      {
        key: 'traffic-jobs.online',
        labelKey: 'permissions.trafficJobs.online',
        crudType: 'section',
        children: [
          { key: 'traffic-jobs.online.createJob', labelKey: 'permissions.trafficJobs.online.createJob', crudType: 'C' },
          {
            key: 'traffic-jobs.online.form',
            labelKey: 'permissions.trafficJobs.online.form',
            crudType: 'section',
            children: [
              { key: 'traffic-jobs.online.form.provider',              labelKey: 'permissions.trafficJobs.online.form.provider',              crudType: 'field' },
              { key: 'traffic-jobs.online.form.agentRef',              labelKey: 'permissions.trafficJobs.online.form.agentRef',              crudType: 'field' },
              { key: 'traffic-jobs.online.form.serviceType',           labelKey: 'permissions.trafficJobs.online.form.serviceType',           crudType: 'field' },
              { key: 'traffic-jobs.online.form.dateTime',              labelKey: 'permissions.trafficJobs.online.form.dateTime',              crudType: 'field' },
              { key: 'traffic-jobs.online.form.clientInfo',            labelKey: 'permissions.trafficJobs.online.form.clientInfo',            crudType: 'field' },
              { key: 'traffic-jobs.online.form.paxCount',              labelKey: 'permissions.trafficJobs.online.form.paxCount',              crudType: 'field' },
              { key: 'traffic-jobs.online.form.route',                 labelKey: 'permissions.trafficJobs.online.form.route',                 crudType: 'field' },
              { key: 'traffic-jobs.online.form.flightInfo',            labelKey: 'permissions.trafficJobs.online.form.flightInfo',            crudType: 'field' },
              { key: 'traffic-jobs.online.form.extras',                labelKey: 'permissions.trafficJobs.online.form.extras',                crudType: 'field' },
              { key: 'traffic-jobs.online.form.requestedVehicleType',  labelKey: 'permissions.trafficJobs.online.form.requestedVehicleType',  crudType: 'field' },
              { key: 'traffic-jobs.online.form.notes',                 labelKey: 'permissions.trafficJobs.online.form.notes',                 crudType: 'field' },
              { key: 'traffic-jobs.online.form.printSign',             labelKey: 'permissions.trafficJobs.online.form.printSign',             crudType: 'field' },
            ],
          },
          {
            key: 'traffic-jobs.online.table',
            labelKey: 'permissions.trafficJobs.online.table',
            crudType: 'section',
            children: [
              { key: 'traffic-jobs.online.table.statusFilter', labelKey: 'permissions.trafficJobs.online.table.statusFilter', crudType: 'R' },
            ],
          },
        ],
      },
      // B2B jobs
      {
        key: 'traffic-jobs.b2b',
        labelKey: 'permissions.trafficJobs.b2b',
        crudType: 'section',
        children: [
          { key: 'traffic-jobs.b2b.createJob', labelKey: 'permissions.trafficJobs.b2b.createJob', crudType: 'C' },
          {
            key: 'traffic-jobs.b2b.form',
            labelKey: 'permissions.trafficJobs.b2b.form',
            crudType: 'section',
            children: [
              { key: 'traffic-jobs.b2b.form.customer',    labelKey: 'permissions.trafficJobs.b2b.form.customer',    crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.serviceType', labelKey: 'permissions.trafficJobs.b2b.form.serviceType', crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.dateTime',    labelKey: 'permissions.trafficJobs.b2b.form.dateTime',    crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.paxCount',    labelKey: 'permissions.trafficJobs.b2b.form.paxCount',    crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.route',       labelKey: 'permissions.trafficJobs.b2b.form.route',       crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.flightInfo',  labelKey: 'permissions.trafficJobs.b2b.form.flightInfo',  crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.meetingInfo', labelKey: 'permissions.trafficJobs.b2b.form.meetingInfo', crudType: 'field' },
              { key: 'traffic-jobs.b2b.form.notes',       labelKey: 'permissions.trafficJobs.b2b.form.notes',       crudType: 'field' },
            ],
          },
          {
            key: 'traffic-jobs.b2b.table',
            labelKey: 'permissions.trafficJobs.b2b.table',
            crudType: 'section',
            children: [
              { key: 'traffic-jobs.b2b.table.statusFilter', labelKey: 'permissions.trafficJobs.b2b.table.statusFilter', crudType: 'R' },
            ],
          },
          { key: 'traffic-jobs.b2b.importJobs', labelKey: 'permissions.trafficJobs.b2b.importJobs', crudType: 'import' },
        ],
      },
    ],
  },

  // ─── AGENTS ───
  {
    key: 'agents',
    labelKey: 'permissions.agents',
    crudType: 'page',
    children: [
      { key: 'agents.addButton',        labelKey: 'permissions.agents.addButton',        crudType: 'C' },
      {
        key: 'agents.table',
        labelKey: 'permissions.agents.table',
        crudType: 'section',
        children: [
          { key: 'agents.table.editButton',   labelKey: 'permissions.agents.table.editButton',   crudType: 'U' },
          { key: 'agents.table.deleteButton', labelKey: 'permissions.agents.table.deleteButton', crudType: 'D' },
          { key: 'agents.table.toggleStatus', labelKey: 'permissions.agents.table.toggleStatus', crudType: 'U' },
        ],
      },
      { key: 'agents.export',           labelKey: 'permissions.agents.export',           crudType: 'export' },
      { key: 'agents.downloadTemplate', labelKey: 'permissions.agents.downloadTemplate', crudType: 'export' },
      { key: 'agents.import',           labelKey: 'permissions.agents.import',           crudType: 'import' },
      {
        key: 'agents.form',
        labelKey: 'permissions.agents.form',
        crudType: 'section',
        children: [
          { key: 'agents.form.legalName',   labelKey: 'permissions.agents.form.legalName',   crudType: 'field' },
          { key: 'agents.form.tradeName',   labelKey: 'permissions.agents.form.tradeName',   crudType: 'field' },
          { key: 'agents.form.taxId',       labelKey: 'permissions.agents.form.taxId',       crudType: 'field' },
          { key: 'agents.form.contactInfo', labelKey: 'permissions.agents.form.contactInfo', crudType: 'field' },
          { key: 'agents.form.currency',    labelKey: 'permissions.agents.form.currency',    crudType: 'field' },
          { key: 'agents.form.refPattern',  labelKey: 'permissions.agents.form.refPattern',  crudType: 'field' },
          { key: 'agents.form.creditLimit', labelKey: 'permissions.agents.form.creditLimit', crudType: 'field' },
          { key: 'agents.form.creditDays',  labelKey: 'permissions.agents.form.creditDays',  crudType: 'field' },
        ],
      },
    ],
  },

  // ─── CUSTOMERS ───
  {
    key: 'customers',
    labelKey: 'permissions.customers',
    crudType: 'page',
    children: [
      { key: 'customers.addButton',        labelKey: 'permissions.customers.addButton',        crudType: 'C' },
      {
        key: 'customers.table',
        labelKey: 'permissions.customers.table',
        crudType: 'section',
        children: [
          { key: 'customers.table.editButton',   labelKey: 'permissions.customers.table.editButton',   crudType: 'U' },
          { key: 'customers.table.deleteButton', labelKey: 'permissions.customers.table.deleteButton', crudType: 'D' },
          { key: 'customers.table.viewButton',   labelKey: 'permissions.customers.table.viewButton',   crudType: 'R' },
          { key: 'customers.table.toggleStatus', labelKey: 'permissions.customers.table.toggleStatus', crudType: 'U' },
        ],
      },
      { key: 'customers.export',           labelKey: 'permissions.customers.export',           crudType: 'export' },
      { key: 'customers.downloadTemplate', labelKey: 'permissions.customers.downloadTemplate', crudType: 'export' },
      { key: 'customers.import',           labelKey: 'permissions.customers.import',           crudType: 'import' },
      {
        key: 'customers.form',
        labelKey: 'permissions.customers.form',
        crudType: 'section',
        children: [
          { key: 'customers.form.legalName',   labelKey: 'permissions.customers.form.legalName',   crudType: 'field' },
          { key: 'customers.form.tradeName',   labelKey: 'permissions.customers.form.tradeName',   crudType: 'field' },
          { key: 'customers.form.taxId',       labelKey: 'permissions.customers.form.taxId',       crudType: 'field' },
          { key: 'customers.form.contactInfo', labelKey: 'permissions.customers.form.contactInfo', crudType: 'field' },
          { key: 'customers.form.currency',    labelKey: 'permissions.customers.form.currency',    crudType: 'field' },
          { key: 'customers.form.creditLimit', labelKey: 'permissions.customers.form.creditLimit', crudType: 'field' },
          { key: 'customers.form.creditDays',  labelKey: 'permissions.customers.form.creditDays',  crudType: 'field' },
        ],
      },
      {
        key: 'customers.detail',
        labelKey: 'permissions.customers.detail',
        crudType: 'section',
        children: [
          {
            key: 'customers.detail.priceList',
            labelKey: 'permissions.customers.detail.priceList',
            crudType: 'section',
            children: [
              { key: 'customers.detail.priceList.addRoute',          labelKey: 'permissions.customers.detail.priceList.addRoute',          crudType: 'C' },
              { key: 'customers.detail.priceList.editPrice',         labelKey: 'permissions.customers.detail.priceList.editPrice',         crudType: 'U' },
              { key: 'customers.detail.priceList.deleteRoute',       labelKey: 'permissions.customers.detail.priceList.deleteRoute',       crudType: 'D' },
              { key: 'customers.detail.priceList.import',            labelKey: 'permissions.customers.detail.priceList.import',            crudType: 'import' },
              { key: 'customers.detail.priceList.downloadTemplate',  labelKey: 'permissions.customers.detail.priceList.downloadTemplate',  crudType: 'export' },
              { key: 'customers.detail.priceList.saveAll',           labelKey: 'permissions.customers.detail.priceList.saveAll',           crudType: 'action' },
            ],
          },
          {
            key: 'customers.detail.importTemplates',
            labelKey: 'permissions.customers.detail.importTemplates',
            crudType: 'section',
            children: [
              { key: 'customers.detail.importTemplates.upload', labelKey: 'permissions.customers.detail.importTemplates.upload', crudType: 'C' },
              { key: 'customers.detail.importTemplates.delete', labelKey: 'permissions.customers.detail.importTemplates.delete', crudType: 'D' },
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
    crudType: 'page',
    children: [
      {
        key: 'finance.invoices',
        labelKey: 'permissions.finance.invoices',
        crudType: 'section',
        children: [
          { key: 'finance.invoices.addButton', labelKey: 'permissions.finance.invoices.addButton', crudType: 'C' },
          {
            key: 'finance.invoices.detail',
            labelKey: 'permissions.finance.invoices.detail',
            crudType: 'section',
            children: [
              { key: 'finance.invoices.detail.editLines',    labelKey: 'permissions.finance.invoices.detail.editLines',    crudType: 'U' },
              { key: 'finance.invoices.detail.addLine',      labelKey: 'permissions.finance.invoices.detail.addLine',      crudType: 'C' },
              { key: 'finance.invoices.detail.deleteLine',   labelKey: 'permissions.finance.invoices.detail.deleteLine',   crudType: 'D' },
              { key: 'finance.invoices.detail.postButton',   labelKey: 'permissions.finance.invoices.detail.postButton',   crudType: 'action' },
              { key: 'finance.invoices.detail.cancelButton', labelKey: 'permissions.finance.invoices.detail.cancelButton', crudType: 'action' },
              { key: 'finance.invoices.detail.applyVat',     labelKey: 'permissions.finance.invoices.detail.applyVat',     crudType: 'action' },
            ],
          },
          { key: 'finance.invoices.recordPayment', labelKey: 'permissions.finance.invoices.recordPayment', crudType: 'action' },
        ],
      },
      { key: 'finance.b2cInvoices', labelKey: 'permissions.finance.b2cInvoices', crudType: 'R' },
      {
        key: 'finance.payments',
        labelKey: 'permissions.finance.payments',
        crudType: 'section',
        children: [
          { key: 'finance.payments.addButton',    labelKey: 'permissions.finance.payments.addButton',    crudType: 'C' },
          { key: 'finance.payments.deleteButton', labelKey: 'permissions.finance.payments.deleteButton', crudType: 'D' },
        ],
      },
      {
        key: 'finance.exports',
        labelKey: 'permissions.finance.exports',
        crudType: 'section',
        children: [
          { key: 'finance.exports.customers',   labelKey: 'permissions.finance.exports.customers',   crudType: 'export' },
          { key: 'finance.exports.suppliers',   labelKey: 'permissions.finance.exports.suppliers',   crudType: 'export' },
          { key: 'finance.exports.invoices',    labelKey: 'permissions.finance.exports.invoices',    crudType: 'export' },
          { key: 'finance.exports.vendorBills', labelKey: 'permissions.finance.exports.vendorBills', crudType: 'export' },
          { key: 'finance.exports.payments',    labelKey: 'permissions.finance.exports.payments',    crudType: 'export' },
          { key: 'finance.exports.journals',    labelKey: 'permissions.finance.exports.journals',    crudType: 'export' },
          { key: 'finance.exports.collections', labelKey: 'permissions.finance.exports.collections', crudType: 'export' },
          { key: 'finance.odooExport',          labelKey: 'permissions.finance.odooExport',          crudType: 'export' },
        ],
      },
    ],
  },

  // ─── REPORTS ───
  {
    key: 'reports',
    labelKey: 'permissions.reports',
    crudType: 'page',
    children: [
      { key: 'reports.dailyDispatch',    labelKey: 'permissions.reports.dailyDispatch',    crudType: 'R' },
      { key: 'reports.driverTrips',      labelKey: 'permissions.reports.driverTrips',      crudType: 'R' },
      { key: 'reports.driverScore',      labelKey: 'permissions.reports.driverScore',      crudType: 'R' },
      { key: 'reports.agentStatement',   labelKey: 'permissions.reports.agentStatement',   crudType: 'R' },
      { key: 'reports.repFees',          labelKey: 'permissions.reports.repFees',          crudType: 'R' },
      { key: 'reports.repScore',         labelKey: 'permissions.reports.repScore',         crudType: 'R' },
      { key: 'reports.guestSurveys',     labelKey: 'permissions.reports.guestSurveys',     crudType: 'R' },
      { key: 'reports.revenue',          labelKey: 'permissions.reports.revenue',          crudType: 'R' },
      { key: 'reports.vehicleCompliance',labelKey: 'permissions.reports.vehicleCompliance',crudType: 'R' },
      { key: 'reports.jobStatus',        labelKey: 'permissions.reports.jobStatus',        crudType: 'R' },
      { key: 'reports.evidence',         labelKey: 'permissions.reports.evidence',         crudType: 'R' },
      { key: 'reports.supplierJobs',     labelKey: 'permissions.reports.supplierJobs',     crudType: 'R' },
      { key: 'reports.carJobs',          labelKey: 'permissions.reports.carJobs',          crudType: 'R' },
      { key: 'reports.visa',             labelKey: 'permissions.reports.visa',             crudType: 'R' },
      { key: 'reports.sales',            labelKey: 'permissions.reports.sales',            crudType: 'R' },
      { key: 'reports.departure',        labelKey: 'permissions.reports.departure',        crudType: 'R' },
      { key: 'reports.flightDelay',      labelKey: 'permissions.reports.flightDelay',      crudType: 'R' },
      { key: 'reports.review',           labelKey: 'permissions.reports.review',           crudType: 'R' },
    ],
  },

  // ─── VEHICLES ───
  {
    key: 'vehicles',
    labelKey: 'permissions.vehicles',
    crudType: 'page',
    children: [
      {
        key: 'vehicles.types',
        labelKey: 'permissions.vehicles.types',
        crudType: 'section',
        children: [
          { key: 'vehicles.types.addButton',  labelKey: 'permissions.vehicles.types.addButton',  crudType: 'C' },
          { key: 'vehicles.types.editButton', labelKey: 'permissions.vehicles.types.editButton', crudType: 'U' },
        ],
      },
      { key: 'vehicles.addButton',        labelKey: 'permissions.vehicles.addButton',        crudType: 'C' },
      {
        key: 'vehicles.table',
        labelKey: 'permissions.vehicles.table',
        crudType: 'section',
        children: [
          { key: 'vehicles.table.editButton',   labelKey: 'permissions.vehicles.table.editButton',   crudType: 'U' },
          { key: 'vehicles.table.deleteButton', labelKey: 'permissions.vehicles.table.deleteButton', crudType: 'D' },
          { key: 'vehicles.table.toggleStatus', labelKey: 'permissions.vehicles.table.toggleStatus', crudType: 'U' },
        ],
      },
      { key: 'vehicles.import',           labelKey: 'permissions.vehicles.import',           crudType: 'import' },
      { key: 'vehicles.export',           labelKey: 'permissions.vehicles.export',           crudType: 'export' },
      { key: 'vehicles.downloadTemplate', labelKey: 'permissions.vehicles.downloadTemplate', crudType: 'export' },
      {
        key: 'vehicles.form',
        labelKey: 'permissions.vehicles.form',
        crudType: 'section',
        children: [
          { key: 'vehicles.form.plateNumber',      labelKey: 'permissions.vehicles.form.plateNumber',      crudType: 'field' },
          { key: 'vehicles.form.vehicleType',      labelKey: 'permissions.vehicles.form.vehicleType',      crudType: 'field' },
          { key: 'vehicles.form.color',            labelKey: 'permissions.vehicles.form.color',            crudType: 'field' },
          { key: 'vehicles.form.brand',            labelKey: 'permissions.vehicles.form.brand',            crudType: 'field' },
          { key: 'vehicles.form.model',            labelKey: 'permissions.vehicles.form.model',            crudType: 'field' },
          { key: 'vehicles.form.makeYear',         labelKey: 'permissions.vehicles.form.makeYear',         crudType: 'field' },
          { key: 'vehicles.form.luggageCapacity',  labelKey: 'permissions.vehicles.form.luggageCapacity',  crudType: 'field' },
          { key: 'vehicles.form.ownership',        labelKey: 'permissions.vehicles.form.ownership',        crudType: 'field' },
        ],
      },
    ],
  },

  // ─── DRIVERS ───
  {
    key: 'drivers',
    labelKey: 'permissions.drivers',
    crudType: 'page',
    children: [
      { key: 'drivers.addButton',        labelKey: 'permissions.drivers.addButton',        crudType: 'C' },
      {
        key: 'drivers.table',
        labelKey: 'permissions.drivers.table',
        crudType: 'section',
        children: [
          { key: 'drivers.table.editButton',       labelKey: 'permissions.drivers.table.editButton',       crudType: 'U' },
          { key: 'drivers.table.deleteButton',     labelKey: 'permissions.drivers.table.deleteButton',     crudType: 'D' },
          { key: 'drivers.table.toggleStatus',     labelKey: 'permissions.drivers.table.toggleStatus',     crudType: 'U' },
          { key: 'drivers.table.uploadAttachment', labelKey: 'permissions.drivers.table.uploadAttachment', crudType: 'action' },
          { key: 'drivers.table.createAccount',    labelKey: 'permissions.drivers.table.createAccount',    crudType: 'action' },
          { key: 'drivers.table.resetPassword',    labelKey: 'permissions.drivers.table.resetPassword',    crudType: 'action' },
        ],
      },
      { key: 'drivers.import',           labelKey: 'permissions.drivers.import',           crudType: 'import' },
      { key: 'drivers.export',           labelKey: 'permissions.drivers.export',           crudType: 'export' },
      { key: 'drivers.downloadTemplate', labelKey: 'permissions.drivers.downloadTemplate', crudType: 'export' },
      {
        key: 'drivers.form',
        labelKey: 'permissions.drivers.form',
        crudType: 'section',
        children: [
          { key: 'drivers.form.name',          labelKey: 'permissions.drivers.form.name',          crudType: 'field' },
          { key: 'drivers.form.mobile',        labelKey: 'permissions.drivers.form.mobile',        crudType: 'field' },
          { key: 'drivers.form.licenseNumber', labelKey: 'permissions.drivers.form.licenseNumber', crudType: 'field' },
          { key: 'drivers.form.licenseExpiry', labelKey: 'permissions.drivers.form.licenseExpiry', crudType: 'field' },
        ],
      },
    ],
  },

  // ─── REPS ───
  {
    key: 'reps',
    labelKey: 'permissions.reps',
    crudType: 'page',
    children: [
      { key: 'reps.addButton',        labelKey: 'permissions.reps.addButton',        crudType: 'C' },
      {
        key: 'reps.table',
        labelKey: 'permissions.reps.table',
        crudType: 'section',
        children: [
          { key: 'reps.table.editButton',       labelKey: 'permissions.reps.table.editButton',       crudType: 'U' },
          { key: 'reps.table.deleteButton',     labelKey: 'permissions.reps.table.deleteButton',     crudType: 'D' },
          { key: 'reps.table.toggleStatus',     labelKey: 'permissions.reps.table.toggleStatus',     crudType: 'U' },
          { key: 'reps.table.uploadAttachment', labelKey: 'permissions.reps.table.uploadAttachment', crudType: 'action' },
          { key: 'reps.table.createAccount',    labelKey: 'permissions.reps.table.createAccount',    crudType: 'action' },
          { key: 'reps.table.resetPassword',    labelKey: 'permissions.reps.table.resetPassword',    crudType: 'action' },
        ],
      },
      { key: 'reps.import',           labelKey: 'permissions.reps.import',           crudType: 'import' },
      { key: 'reps.export',           labelKey: 'permissions.reps.export',           crudType: 'export' },
      { key: 'reps.downloadTemplate', labelKey: 'permissions.reps.downloadTemplate', crudType: 'export' },
      {
        key: 'reps.form',
        labelKey: 'permissions.reps.form',
        crudType: 'section',
        children: [
          { key: 'reps.form.name',         labelKey: 'permissions.reps.form.name',         crudType: 'field' },
          { key: 'reps.form.mobile',       labelKey: 'permissions.reps.form.mobile',       crudType: 'field' },
          { key: 'reps.form.feePerFlight', labelKey: 'permissions.reps.form.feePerFlight', crudType: 'field' },
        ],
      },
    ],
  },

  // ─── SUPPLIERS ───
  {
    key: 'suppliers',
    labelKey: 'permissions.suppliers',
    crudType: 'page',
    children: [
      { key: 'suppliers.addButton',        labelKey: 'permissions.suppliers.addButton',        crudType: 'C' },
      {
        key: 'suppliers.table',
        labelKey: 'permissions.suppliers.table',
        crudType: 'section',
        children: [
          { key: 'suppliers.table.editButton',   labelKey: 'permissions.suppliers.table.editButton',   crudType: 'U' },
          { key: 'suppliers.table.deleteButton', labelKey: 'permissions.suppliers.table.deleteButton', crudType: 'D' },
          { key: 'suppliers.table.toggleStatus', labelKey: 'permissions.suppliers.table.toggleStatus', crudType: 'U' },
          { key: 'suppliers.table.createAccount',labelKey: 'permissions.suppliers.table.createAccount',crudType: 'action' },
          { key: 'suppliers.table.resetPassword',labelKey: 'permissions.suppliers.table.resetPassword',crudType: 'action' },
        ],
      },
      { key: 'suppliers.export',           labelKey: 'permissions.suppliers.export',           crudType: 'export' },
      { key: 'suppliers.downloadTemplate', labelKey: 'permissions.suppliers.downloadTemplate', crudType: 'export' },
      { key: 'suppliers.import',           labelKey: 'permissions.suppliers.import',           crudType: 'import' },
      {
        key: 'suppliers.form',
        labelKey: 'permissions.suppliers.form',
        crudType: 'section',
        children: [
          { key: 'suppliers.form.legalName',   labelKey: 'permissions.suppliers.form.legalName',   crudType: 'field' },
          { key: 'suppliers.form.tradeName',   labelKey: 'permissions.suppliers.form.tradeName',   crudType: 'field' },
          { key: 'suppliers.form.taxId',       labelKey: 'permissions.suppliers.form.taxId',       crudType: 'field' },
          { key: 'suppliers.form.contactInfo', labelKey: 'permissions.suppliers.form.contactInfo', crudType: 'field' },
        ],
      },
    ],
  },

  // ─── LOCATIONS ───
  {
    key: 'locations',
    labelKey: 'permissions.locations',
    crudType: 'page',
    children: [
      {
        key: 'locations.countries',
        labelKey: 'permissions.locations.countries',
        crudType: 'section',
        children: [
          { key: 'locations.countries.addButton',  labelKey: 'permissions.locations.countries.addButton',  crudType: 'C' },
          { key: 'locations.countries.editButton', labelKey: 'permissions.locations.countries.editButton', crudType: 'U' },
        ],
      },
      {
        key: 'locations.airports',
        labelKey: 'permissions.locations.airports',
        crudType: 'section',
        children: [
          { key: 'locations.airports.addButton',    labelKey: 'permissions.locations.airports.addButton',    crudType: 'C' },
          { key: 'locations.airports.editButton',   labelKey: 'permissions.locations.airports.editButton',   crudType: 'U' },
          { key: 'locations.airports.deleteButton', labelKey: 'permissions.locations.airports.deleteButton', crudType: 'D' },
        ],
      },
      {
        key: 'locations.cities',
        labelKey: 'permissions.locations.cities',
        crudType: 'section',
        children: [
          { key: 'locations.cities.addButton',    labelKey: 'permissions.locations.cities.addButton',    crudType: 'C' },
          { key: 'locations.cities.editButton',   labelKey: 'permissions.locations.cities.editButton',   crudType: 'U' },
          { key: 'locations.cities.deleteButton', labelKey: 'permissions.locations.cities.deleteButton', crudType: 'D' },
        ],
      },
      {
        key: 'locations.zones',
        labelKey: 'permissions.locations.zones',
        crudType: 'section',
        children: [
          { key: 'locations.zones.addButton',    labelKey: 'permissions.locations.zones.addButton',    crudType: 'C' },
          { key: 'locations.zones.editButton',   labelKey: 'permissions.locations.zones.editButton',   crudType: 'U' },
          { key: 'locations.zones.deleteButton', labelKey: 'permissions.locations.zones.deleteButton', crudType: 'D' },
        ],
      },
      {
        key: 'locations.hotels',
        labelKey: 'permissions.locations.hotels',
        crudType: 'section',
        children: [
          { key: 'locations.hotels.addButton',    labelKey: 'permissions.locations.hotels.addButton',    crudType: 'C' },
          { key: 'locations.hotels.editButton',   labelKey: 'permissions.locations.hotels.editButton',   crudType: 'U' },
          { key: 'locations.hotels.deleteButton', labelKey: 'permissions.locations.hotels.deleteButton', crudType: 'D' },
        ],
      },
      { key: 'locations.export',           labelKey: 'permissions.locations.export',           crudType: 'export' },
      { key: 'locations.downloadTemplate', labelKey: 'permissions.locations.downloadTemplate', crudType: 'export' },
      { key: 'locations.import',           labelKey: 'permissions.locations.import',           crudType: 'import' },
    ],
  },

  // ─── COMPANY SETTINGS ───
  {
    key: 'company',
    labelKey: 'permissions.company',
    crudType: 'page',
    children: [
      { key: 'company.editSettings',  labelKey: 'permissions.company.editSettings',  crudType: 'U' },
      { key: 'company.uploadLogo',    labelKey: 'permissions.company.uploadLogo',    crudType: 'action' },
      { key: 'company.uploadFavicon', labelKey: 'permissions.company.uploadFavicon', crudType: 'action' },
    ],
  },

  // ─── USERS & ROLES ───
  {
    key: 'users',
    labelKey: 'permissions.users',
    crudType: 'page',
    children: [
      { key: 'users.addButton', labelKey: 'permissions.users.addButton', crudType: 'C' },
      {
        key: 'users.table',
        labelKey: 'permissions.users.table',
        crudType: 'section',
        children: [
          { key: 'users.table.editButton', labelKey: 'permissions.users.table.editButton', crudType: 'U' },
          { key: 'users.table.changeRole', labelKey: 'permissions.users.table.changeRole', crudType: 'action' },
          { key: 'users.table.deactivate', labelKey: 'permissions.users.table.deactivate', crudType: 'D' },
        ],
      },
      {
        key: 'users.roles',
        labelKey: 'permissions.users.roles',
        crudType: 'section',
        children: [
          { key: 'users.roles.addButton',       labelKey: 'permissions.users.roles.addButton',       crudType: 'C' },
          { key: 'users.roles.editButton',      labelKey: 'permissions.users.roles.editButton',      crudType: 'U' },
          { key: 'users.roles.deleteButton',    labelKey: 'permissions.users.roles.deleteButton',    crudType: 'D' },
          { key: 'users.roles.editPermissions', labelKey: 'permissions.users.roles.editPermissions', crudType: 'action' },
        ],
      },
    ],
  },

  // ─── GUEST BOOKINGS (B2C) ───
  {
    key: 'guest-bookings',
    labelKey: 'permissions.guestBookings',
    crudType: 'page',
    children: [
      { key: 'guest-bookings.convert', labelKey: 'permissions.guestBookings.convert', crudType: 'action' },
      { key: 'guest-bookings.cancel',  labelKey: 'permissions.guestBookings.cancel',  crudType: 'D' },
    ],
  },

  // ─── PUBLIC PRICES (B2C) ───
  {
    key: 'public-prices',
    labelKey: 'permissions.publicPrices',
    crudType: 'page',
    children: [
      { key: 'public-prices.bulk',   labelKey: 'permissions.publicPrices.bulk',   crudType: 'action' },
      { key: 'public-prices.delete', labelKey: 'permissions.publicPrices.delete', crudType: 'D' },
    ],
  },

  // ─── B2C EXTRAS ───
  {
    key: 'extras',
    labelKey: 'permissions.extras',
    crudType: 'page',
    children: [
      { key: 'extras.addButton',    labelKey: 'permissions.extras.addButton',    crudType: 'C' },
      { key: 'extras.editButton',   labelKey: 'permissions.extras.editButton',   crudType: 'U' },
      { key: 'extras.deleteButton', labelKey: 'permissions.extras.deleteButton', crudType: 'D' },
    ],
  },

  // ─── DRIVER TARIFFS ───
  {
    key: 'driver-tariffs',
    labelKey: 'permissions.driverTariffs',
    crudType: 'page',
    children: [
      { key: 'driver-tariffs.upsert', labelKey: 'permissions.driverTariffs.upsert', crudType: 'action' },
      { key: 'driver-tariffs.delete', labelKey: 'permissions.driverTariffs.delete', crudType: 'D' },
    ],
  },

  // ─── JOB LOCKS ───
  {
    key: 'job-control',
    labelKey: 'permissions.jobControl',
    crudType: 'page',
  },
  {
    key: 'job-locks',
    labelKey: 'permissions.jobLocks',
    crudType: 'page',
    children: [
      { key: 'job-locks.dispatcher', labelKey: 'permissions.jobLocks.dispatcher', crudType: 'R' },
      { key: 'job-locks.driver',     labelKey: 'permissions.jobLocks.driver',     crudType: 'R' },
      { key: 'job-locks.rep',        labelKey: 'permissions.jobLocks.rep',        crudType: 'R' },
      { key: 'job-locks.supplier',   labelKey: 'permissions.jobLocks.supplier',   crudType: 'R' },
      { key: 'job-locks.edit',       labelKey: 'permissions.jobLocks.edit',       crudType: 'U' },
      { key: 'job-locks.b2c',        labelKey: 'permissions.jobLocks.b2c',        crudType: 'U' },
      { key: 'job-locks.online',     labelKey: 'permissions.jobLocks.online',     crudType: 'U' },
    ],
  },

  // ─── ACTIVITY LOGS ───
  {
    key: 'activity-logs',
    labelKey: 'permissions.activityLogs',
    crudType: 'page',
    children: [
      { key: 'activity-logs.export', labelKey: 'permissions.activityLogs.export', crudType: 'export' },
    ],
  },

  // ─── WHATSAPP NOTIFICATIONS ───
  {
    key: 'whatsapp',
    labelKey: 'permissions.whatsapp',
    crudType: 'page',
    children: [
      {
        key: 'whatsapp.settings',
        labelKey: 'permissions.whatsapp.settings',
        crudType: 'section',
        children: [
          { key: 'whatsapp.settings.editSettings', labelKey: 'permissions.whatsapp.settings.editSettings', crudType: 'U' },
        ],
      },
      { key: 'whatsapp.logs',        labelKey: 'permissions.whatsapp.logs',        crudType: 'R' },
      { key: 'whatsapp.testSend',    labelKey: 'permissions.whatsapp.testSend',    crudType: 'action' },
      { key: 'whatsapp.uploadMedia', labelKey: 'permissions.whatsapp.uploadMedia', crudType: 'action' },
    ],
  },

  // ─── B2C WEBSITE CONTENT ───
  {
    key: 'website-content',
    labelKey: 'permissions.websiteContent',
    crudType: 'section',
    children: [
      { key: 'website-content.cityPages', labelKey: 'permissions.websiteContent.cityPages', crudType: 'section' },
      { key: 'website-content.blog',      labelKey: 'permissions.websiteContent.blog',      crudType: 'section' },
      { key: 'website-content.pageSeo',   labelKey: 'permissions.websiteContent.pageSeo',   crudType: 'section' },
      { key: 'website-content.pages',     labelKey: 'permissions.websiteContent.pages',     crudType: 'section' },
    ],
  },
  {
    key: 'contact-messages',
    labelKey: 'permissions.contactMessages',
    crudType: 'section',
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

/**
 * Find a single node by key in the registry tree.
 */
export function findNode(
  key: string,
  nodes: PermissionNode[] = PERMISSION_REGISTRY,
): PermissionNode | null {
  for (const node of nodes) {
    if (node.key === key) return node;
    if (node.children) {
      const found = findNode(key, node.children);
      if (found) return found;
    }
  }
  return null;
}
