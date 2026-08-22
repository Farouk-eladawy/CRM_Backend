import { Controller, Get, Query, Param, Res, UseGuards, BadRequestException, NotFoundException, ParseUUIDPipe, InternalServerErrorException } from '@nestjs/common';
import * as express from 'express';
import { ExportService } from './export.service.js';
import { GoogleDriveService, isDriveFileId } from '../google-drive/google-drive.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';

@Controller('export/odoo')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
@Roles('ADMIN', 'MANAGER', 'ACCOUNTANT')
export class ExportController {
  constructor(
    private readonly exportService: ExportService,
    private readonly googleDriveService: GoogleDriveService,
  ) {}

  @Get('dispatch')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('dispatch.exportButton')
  async exportDispatchDay(
    @Query('date') date: string,
    @Res() res: express.Response,
  ) {
    if (!date) {
      throw new BadRequestException('date query parameter is required');
    }
    const buffer = await this.exportService.exportDispatchDay(date);
    this.sendXlsx(res, buffer, `dispatch_${date}`);
  }

  @Get('rep-fees')
  @Permissions('reports.repFees')
  async exportRepFees(
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) {
      throw new BadRequestException('from and to query parameters are required');
    }
    const buffer = await this.exportService.exportRepFees(from, to);
    this.sendXlsx(res, buffer, `rep_fees_${from}_to_${to}`);
  }

  @Get('customers')
  @Permissions('finance.exports.customers')
  async exportCustomers(@Res() res: express.Response) {
    const buffer = await this.exportService.exportCustomers();
    this.sendXlsx(res, buffer, 'odoo_customers');
  }

  @Get('suppliers')
  @Permissions('finance.exports.suppliers')
  async exportSuppliers(@Res() res: express.Response) {
    const buffer = await this.exportService.exportSuppliers();
    this.sendXlsx(res, buffer, 'odoo_suppliers');
  }

  @Get('invoices')
  @Permissions('finance.exports.invoices')
  async exportInvoices(
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
    @Res() res: express.Response,
  ) {
    const buffer = await this.exportService.exportInvoices(dateFrom, dateTo);
    this.sendXlsx(res, buffer, 'odoo_customer_invoices');
  }

  @Get('vendor-bills')
  @Permissions('finance.exports.vendorBills')
  async exportVendorBills(
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
    @Res() res: express.Response,
  ) {
    const buffer = await this.exportService.exportVendorBills(dateFrom, dateTo);
    this.sendXlsx(res, buffer, 'odoo_vendor_bills');
  }

  @Get('payments')
  @Permissions('finance.exports.payments')
  async exportPayments(
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
    @Res() res: express.Response,
  ) {
    const buffer = await this.exportService.exportPayments(dateFrom, dateTo);
    this.sendXlsx(res, buffer, 'odoo_payments');
  }

  @Get('journals')
  @Permissions('finance.exports.journals')
  async exportJournalEntries(
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
    @Res() res: express.Response,
  ) {
    const buffer = await this.exportService.exportJournalEntries(dateFrom, dateTo);
    this.sendXlsx(res, buffer, 'odoo_journal_entries');
  }

  @Get('collections')
  @Permissions('finance.exports.collections')
  async exportCollections(
    @Query('status') status: string,
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
    @Res() res: express.Response,
  ) {
    const buffer = await this.exportService.exportCollections(status, dateFrom, dateTo);
    this.sendXlsx(res, buffer, 'odoo_collections');
  }

  @Get('client-signs')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('dispatch.exportButton', 'traffic-jobs.online.createJob')
  async exportClientSigns(
    @Query('date') date: string,
    @Res() res: express.Response,
  ) {
    if (!date) {
      throw new BadRequestException('date query parameter is required');
    }
    try {
      const buffer = await this.exportService.generateClientSigns(date);
      const dateStr = new Date().toISOString().split('T')[0];
      res.set({
        'Content-Type': 'application/pdf',
        'Content-Disposition': `inline; filename="client_signs_${date}_${dateStr}.pdf"`,
        'Content-Length': buffer.length.toString(),
      });
      res.end(buffer);
    } catch (err: any) {
      if (err.message === 'NO_SIGN_JOBS') {
        throw new NotFoundException('No jobs with print sign for this date');
      }
      throw err;
    }
  }

  @Get('daily-dispatch')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('reports.dailyDispatch')
  async exportDailyDispatch(
    @Query('date') date: string,
    @Res() res: express.Response,
  ) {
    if (!date) {
      throw new BadRequestException('date query parameter is required');
    }
    const buffer = await this.exportService.exportDailyDispatchReport(date);
    this.sendXlsx(res, buffer, `daily_dispatch_${date}`);
  }

  @Get('driver-trips')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.driverTrips')
  async exportDriverTrips(
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) {
      throw new BadRequestException('from and to query parameters are required');
    }
    const buffer = await this.exportService.exportDriverTrips(from, to);
    this.sendXlsx(res, buffer, `driver_trips_${from}_${to}`);
  }

  @Get('agent-statement/:agentId')
  @Roles('ADMIN', 'MANAGER', 'ACCOUNTANT')
  @Permissions('reports.agentStatement')
  async exportAgentStatement(
    @Param('agentId') agentId: string,
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) {
      throw new BadRequestException('from and to query parameters are required');
    }
    const buffer = await this.exportService.exportAgentStatement(agentId, from, to);
    this.sendXlsx(res, buffer, `agent_statement_${from}_${to}`);
  }

  @Get('revenue')
  @Permissions('reports.revenue')
  async exportRevenue(
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) {
      throw new BadRequestException('from and to query parameters are required');
    }
    const buffer = await this.exportService.exportRevenue(from, to);
    this.sendXlsx(res, buffer, `revenue_${from}_${to}`);
  }

  @Get('vehicle-compliance')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('reports.vehicleCompliance')
  async exportVehicleCompliance(@Res() res: express.Response) {
    const buffer = await this.exportService.exportVehicleCompliance();
    this.sendXlsx(res, buffer, 'vehicle_compliance');
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/car-jobs/vehicles
  // Lightweight list of owned+active vehicles for the car jobs filter dropdown.
  // ──────────────────────────────────────────────
  @Get('car-jobs/vehicles')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.carJobs')
  getCarJobsVehicles() {
    return this.exportService.getOwnedActiveVehicles();
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/car-jobs
  // Car Jobs report — filterable by date range and owned vehicle.
  // ──────────────────────────────────────────────
  @Get('car-jobs')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.carJobs')
  async getCarJobsReport(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('vehicleId') vehicleId?: string,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    return this.exportService.getCarJobsReport({ from, to, vehicleId });
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/supplier-jobs
  // Supplier Jobs report — filterable by date range, supplier, and supplier status.
  // ──────────────────────────────────────────────
  @Get('supplier-jobs')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.supplierJobs')
  async getSupplierJobsReport(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('supplierId') supplierId?: string,
    @Query('supplierStatus') supplierStatus?: string,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    return this.exportService.getSupplierJobsReport({ from, to, supplierId, supplierStatus });
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/visa
  // Visa report XLSX export — date range filter.
  // ──────────────────────────────────────────────
  @Get('visa')
  @Permissions('reports.visa')
  async exportVisa(
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportVisaReport(from, to);
    this.sendXlsx(res, buffer, `visa_${from}_${to}`);
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/sales
  // Sales report XLSX export — date range filter.
  // ──────────────────────────────────────────────
  @Get('sales')
  @Permissions('reports.sales')
  async exportSales(
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportSalesReport(from, to);
    this.sendXlsx(res, buffer, `sales_${from}_${to}`);
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/evidence-data/:jobId
  // Returns structured JSON for evidence HTML rendering on the client.
  // ──────────────────────────────────────────────
  @Get('evidence-data/:jobId')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.evidence')
  async getEvidenceData(@Param('jobId', ParseUUIDPipe) jobId: string) {
    return this.exportService.getEvidenceData(jobId);
  }

  @Get('evidence-pdf/:jobId')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.evidence')
  async downloadEvidencePdf(
    @Param('jobId', ParseUUIDPipe) jobId: string,
    @Res() res: express.Response,
  ) {
    try {
      const buffer = await this.exportService.generateJobEvidencePdf(jobId);
      res.set({
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="evidence_${jobId}.pdf"`,
        'Content-Length': buffer.length.toString(),
      });
      res.end(buffer);
    } catch (err: any) {
      if (err?.status === 404) throw new NotFoundException(err.message);
      throw new InternalServerErrorException('Failed to generate evidence PDF');
    }
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/evidence-zip/:jobId
  // Download all evidence images for a job as a ZIP file.
  // ──────────────────────────────────────────────

  @Get('evidence-zip/:jobId')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.evidence')
  async downloadEvidenceZip(
    @Param('jobId', ParseUUIDPipe) jobId: string,
    @Res() res: express.Response,
  ) {
    try {
      await this.exportService.streamEvidenceZip(jobId, res);
    } catch (err: any) {
      if (err?.status === 404) throw new NotFoundException(err.message);
      throw new InternalServerErrorException('Failed to generate evidence ZIP');
    }
  }

  // ──────────────────────────────────────────────
  // GET /export/odoo/evidence-file/:fileId
  // Proxy a Drive file through the backend (JWT-guarded).
  // Accessible to all dashboard roles — dispatchers/managers view evidence images.
  // ──────────────────────────────────────────────

  @Get('evidence-file/:fileId')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.evidence')
  async proxyEvidenceFile(
    @Param('fileId') fileId: string,
    @Res() res: express.Response,
  ) {
    if (!isDriveFileId(fileId)) {
      throw new BadRequestException('Invalid file ID');
    }

    const result = await this.googleDriveService.getFileStream(fileId);
    if (!result) {
      throw new NotFoundException('File not found or Drive not configured');
    }

    res.set({
      'Content-Type': result.mimeType,
      'Cache-Control': 'private, max-age=3600',
    });
    result.stream.pipe(res);
  }

  @Get('evidence-excel')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER', 'ACCOUNTANT')
  @Permissions('reports.evidence')
  async exportEvidenceExcel(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('status') status: string,
    @Query('agentId') agentId: string,
    @Query('repId') repId: string,
    @Query('driverId') driverId: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportEvidenceReport(from, to, status || undefined, agentId || undefined, repId || undefined, driverId || undefined);
    this.sendXlsx(res, buffer, `evidence_${from}_${to}`);
  }

  @Get('driver-score')
  @Permissions('reports.driverScore')
  async exportDriverScore(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('driverId') driverId: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportDriverScoreReport(from, to, driverId || undefined);
    this.sendXlsx(res, buffer, `driver_score_${from}_${to}`);
  }

  @Get('rep-score')
  @Permissions('reports.repScore')
  async exportRepScore(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('repId') repId: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportRepScoreReport(from, to, repId || undefined);
    this.sendXlsx(res, buffer, `rep_score_${from}_${to}`);
  }

  @Get('guest-surveys')
  @Permissions('reports.guestSurveys')
  async exportGuestSurveys(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('repId') repId: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportGuestSurveyReport(from, to, repId || undefined);
    this.sendXlsx(res, buffer, `guest_surveys_${from}_${to}`);
  }

  @Get('job-status')
  @Permissions('reports.jobStatus')
  async exportJobStatus(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('status') status: string,
    @Query('repId') repId: string,
    @Query('repStatus') repStatus: string,
    @Query('driverStatus') driverStatus: string,
    @Query('serviceType') serviceType: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportJobStatusReport(from, to, status, repId, repStatus, driverStatus, serviceType);
    this.sendXlsx(res, buffer, `job_status_${from}_${to}`);
  }

  @Get('departure')
  @Permissions('reports.departure')
  async exportDeparture(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('serviceType') serviceType: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportDepartureReport(from, to, serviceType || undefined);
    this.sendXlsx(res, buffer, `departure_${from}_${to}`);
  }

  @Get('flight-delay')
  @Permissions('reports.flightDelay')
  async exportFlightDelay(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('repName') repName: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportFlightDelayReport(from, to, repName || undefined);
    this.sendXlsx(res, buffer, `flight_delay_${from}_${to}`);
  }

  @Get('supplier-jobs-excel')
  @Permissions('reports.supplierJobs')
  async exportSupplierJobsExcel(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('supplierId') supplierId: string,
    @Query('supplierStatus') supplierStatus: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportSupplierJobsExcel(from, to, supplierId || undefined, supplierStatus || undefined);
    this.sendXlsx(res, buffer, `supplier_jobs_${from}_${to}`);
  }

  @Get('car-jobs-excel')
  @Permissions('reports.carJobs')
  async exportCarJobsExcel(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('vehicleId') vehicleId: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportCarJobsExcel(from, to, vehicleId || undefined);
    this.sendXlsx(res, buffer, `car_jobs_${from}_${to}`);
  }

  @Get('review')
  @Permissions('reports.review')
  async exportReview(
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('status') status: string,
    @Res() res: express.Response,
  ) {
    if (!from || !to) throw new BadRequestException('from and to are required');
    const buffer = await this.exportService.exportReviewReport(from, to, status || undefined);
    this.sendXlsx(res, buffer, `review_${from}_${to}`);
  }

  private sendXlsx(res: express.Response, buffer: Buffer, filename: string) {
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type':
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="${filename}_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }
}
