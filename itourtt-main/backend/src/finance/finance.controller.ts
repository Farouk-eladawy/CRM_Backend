import {
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Body,
  Query,
  Res,
  UseGuards,
  ParseUUIDPipe,
  BadRequestException,
} from '@nestjs/common';
import type { Response } from 'express';
import { FinanceService } from './finance.service.js';
import { InvoiceExportService } from './invoice-export.service.js';
import { OdooExportService } from './odoo-export.service.js';
import { B2CInvoiceService } from '../b2c/b2c-invoice.service.js';
import { CreateDriverFeeDto } from './dto/create-driver-fee.dto.js';
import { CreateRepFeeDto } from './dto/create-rep-fee.dto.js';
import { CreateSupplierCostDto } from './dto/create-supplier-cost.dto.js';
import { CreateInvoiceDto } from './dto/create-invoice.dto.js';
import { CreatePaymentDto } from './dto/create-payment.dto.js';
import { GenerateCustomerInvoicesDto } from './dto/create-customer-invoice.dto.js';
import { UpdateInvoiceLinesDto } from './dto/update-invoice-lines.dto.js';
import { UpdateInvoiceStatusDto } from './dto/update-invoice-status.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional, IsString, IsDateString } from 'class-validator';

class RepDailyFeeQueryDto {
  @IsDateString()
  date!: string;
}

class InvoiceListQueryDto extends PaginationDto {
  @IsOptional()
  @IsString()
  agentId?: string;

  @IsOptional()
  @IsString()
  status?: string;
}

class CustomerInvoiceListQueryDto extends PaginationDto {
  @IsOptional()
  @IsString()
  customerId?: string;

  @IsOptional()
  @IsString()
  invoiceType?: string;

  @IsOptional()
  @IsString()
  status?: string;
}

class B2CInvoiceListQueryDto extends PaginationDto {
  @IsOptional()
  @IsString()
  search?: string;

  @IsOptional()
  @IsDateString()
  dateFrom?: string;

  @IsOptional()
  @IsDateString()
  dateTo?: string;

  @IsOptional()
  @IsString()
  status?: string;
}

@Controller('finance')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
@Roles('ADMIN', 'MANAGER', 'ACCOUNTANT')
export class FinanceController {
  constructor(
    private readonly financeService: FinanceService,
    private readonly invoiceExportService: InvoiceExportService,
    private readonly odooExportService: OdooExportService,
    private readonly b2cInvoiceService: B2CInvoiceService,
  ) {}

  // ─── Driver Fees ─────────────────────────────

  @Post('driver-fees')
  @Permissions('finance')
  async createDriverFee(
    @Body() dto: CreateDriverFeeDto,
    @CurrentUser('id') userId: string,
  ) {
    const fee = await this.financeService.createDriverFee(dto, userId);
    return new ApiResponse(fee, 'Driver fee created successfully');
  }

  // ─── Rep Fees ────────────────────────────────

  @Post('rep-fees')
  @Permissions('finance')
  async createRepFee(
    @Body() dto: CreateRepFeeDto,
    @CurrentUser('id') userId: string,
  ) {
    const fee = await this.financeService.createRepFee(dto, userId);
    return new ApiResponse(fee, 'Rep fee created successfully');
  }

  @Get('rep-fees/:repId/daily')
  @Permissions('finance')
  async getRepDailyFees(
    @Param('repId', ParseUUIDPipe) repId: string,
    @Query() query: RepDailyFeeQueryDto,
  ) {
    const result = await this.financeService.getRepDailyFees(repId, query.date);
    return new ApiResponse(result);
  }

  // ─── Supplier Costs ──────────────────────────

  @Post('supplier-costs')
  @Permissions('finance')
  async createSupplierCost(
    @Body() dto: CreateSupplierCostDto,
    @CurrentUser('id') userId: string,
  ) {
    const cost = await this.financeService.createSupplierCost(dto, userId);
    return new ApiResponse(cost, 'Supplier cost created successfully');
  }

  // ─── Invoices ────────────────────────────────

  @Post('invoices')
  @Permissions('finance.invoices.addButton')
  async createInvoice(
    @Body() dto: CreateInvoiceDto,
    @CurrentUser('id') userId: string,
  ) {
    const invoice = await this.financeService.createInvoice(dto, userId);
    return new ApiResponse(invoice, 'Invoice created successfully');
  }

  @Get('invoices')
  @Permissions('finance.invoices')
  async listInvoices(@Query() query: InvoiceListQueryDto) {
    const { agentId, status, ...pagination } = query;
    return this.financeService.listInvoices(pagination, agentId, status);
  }

  @Get('invoices/:id')
  @Permissions('finance.invoices')
  async getInvoice(@Param('id', ParseUUIDPipe) id: string) {
    const invoice = await this.financeService.getInvoice(id);
    return new ApiResponse(invoice);
  }

  @Patch('invoices/:id/lines')
  @Permissions('finance.invoices.detail.editLines')
  async updateInvoiceLines(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: UpdateInvoiceLinesDto,
  ) {
    const invoice = await this.financeService.updateInvoiceLines(id, dto);
    return new ApiResponse(invoice, 'Invoice lines updated successfully');
  }

  @Patch('invoices/:id/status')
  @Permissions('finance.invoices.detail.postButton')
  async updateInvoiceStatus(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: UpdateInvoiceStatusDto,
  ) {
    const invoice = await this.financeService.updateInvoiceStatus(id, dto);
    return new ApiResponse(invoice, 'Invoice status updated successfully');
  }

  // ─── Payments ────────────────────────────────

  @Post('payments')
  @Permissions('finance.payments.addButton')
  async createPayment(
    @Body() dto: CreatePaymentDto,
    @CurrentUser('id') userId: string,
  ) {
    const payment = await this.financeService.createPayment(dto, userId);
    return new ApiResponse(payment, 'Payment recorded successfully');
  }

  // ─── Job Financials ──────────────────────────

  @Get('jobs/:jobId/financials')
  @Permissions('finance')
  async getJobFinancials(
    @Param('jobId', ParseUUIDPipe) jobId: string,
  ) {
    const financials = await this.financeService.getJobFinancials(jobId);
    return new ApiResponse(financials);
  }

  // ─── Customer Invoices ─────────────────────────

  @Post('customer-invoices/generate')
  @Permissions('finance.invoices.addButton')
  async generateCustomerInvoices(
    @Body() dto: GenerateCustomerInvoicesDto,
    @CurrentUser('id') userId: string,
  ) {
    const result = await this.financeService.generateCustomerInvoices(dto, userId);
    return new ApiResponse(result, 'Customer invoices generated successfully');
  }

  @Get('customer-invoices')
  @Permissions('finance.invoices')
  async listCustomerInvoices(@Query() query: CustomerInvoiceListQueryDto) {
    const { customerId, invoiceType, status, ...pagination } = query;
    return this.financeService.listCustomerInvoices(pagination, customerId, invoiceType, status);
  }

  @Get('customer-invoices/:id')
  @Permissions('finance.invoices')
  async getCustomerInvoice(@Param('id', ParseUUIDPipe) id: string) {
    const invoice = await this.financeService.getCustomerInvoice(id);
    return new ApiResponse(invoice);
  }

  // ─── B2C Guest Invoices ───────────────────────

  @Get('b2c-invoices')
  @Permissions('finance.b2cInvoices')
  async listB2CInvoices(@Query() query: B2CInvoiceListQueryDto) {
    return this.b2cInvoiceService.listAll(query);
  }

  @Get('b2c-invoices/:id/pdf')
  @Permissions('finance.b2cInvoices')
  async getB2CInvoicePdf(
    @Param('id', ParseUUIDPipe) id: string,
    @Res() res: Response,
  ) {
    const { buffer, filename } = await this.b2cInvoiceService.getPdfById(id);
    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  // ─── Agent Options & Jobs for Invoice ───────

  @Get('agent-options')
  @Permissions('finance.invoices')
  async getAgentOptions() {
    const agents = await this.financeService.getAgentOptions();
    return new ApiResponse(agents);
  }

  @Get('customer-options')
  @Permissions('finance.invoices')
  async getCustomerOptions() {
    const customers = await this.financeService.getCustomerOptions();
    return new ApiResponse(customers);
  }

  @Get('customer-jobs')
  @Permissions('finance.invoices')
  async getCustomerJobsForInvoice(
    @Query('customerId', ParseUUIDPipe) customerId: string,
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
  ) {
    if (!dateFrom || !dateTo) {
      throw new BadRequestException('dateFrom and dateTo query parameters are required');
    }
    const jobs = await this.financeService.getCustomerJobsForInvoice(customerId, dateFrom, dateTo);
    return new ApiResponse(jobs);
  }

  @Get('agent-jobs')
  @Permissions('finance.invoices')
  async getAgentJobsForInvoice(
    @Query('agentId', ParseUUIDPipe) agentId: string,
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
  ) {
    if (!dateFrom || !dateTo) {
      throw new BadRequestException('dateFrom and dateTo query parameters are required');
    }
    const jobs = await this.financeService.getAgentJobsForInvoice(agentId, dateFrom, dateTo);
    return new ApiResponse(jobs);
  }

  // ─── Invoice Export (PDF / Excel) ───────────

  @Get('invoices/:id/pdf')
  @Permissions('finance.invoices')
  async getInvoicePdf(
    @Param('id', ParseUUIDPipe) id: string,
    @CurrentUser('id') userId: string,
    @Res() res: Response,
  ) {
    const buffer = await this.invoiceExportService.generateInvoicePdf(id, userId);
    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `inline; filename="invoice_${id}.pdf"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('invoices/:id/excel')
  @Permissions('finance.invoices')
  async getInvoiceExcel(
    @Param('id', ParseUUIDPipe) id: string,
    @CurrentUser('id') userId: string,
    @Res() res: Response,
  ) {
    const buffer = await this.invoiceExportService.generateInvoiceExcel(id, userId);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="invoice_${id}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  // ─── Collections ──────────────────────────────

  @Get('collections')
  @Permissions('finance')
  async getCollections(
    @Query('status') status?: string,
    @Query('dateFrom') dateFrom?: string,
    @Query('dateTo') dateTo?: string,
  ) {
    const result = await this.financeService.getCollections({ status, dateFrom, dateTo });
    return new ApiResponse(result);
  }

  @Patch('collections/:jobId/liquidate')
  @Permissions('finance')
  async liquidateCollection(
    @CurrentUser('id') userId: string,
    @Param('jobId', ParseUUIDPipe) jobId: string,
    @Body() dto: { receiptNo: string },
  ) {
    if (!dto.receiptNo?.trim()) {
      throw new BadRequestException('Receipt number is required');
    }
    const result = await this.financeService.liquidateCollection(jobId, dto.receiptNo.trim(), userId);
    return new ApiResponse(result, 'Collection liquidated successfully');
  }

  // ─── Odoo ERP Exports ─────────────────────────

  @Get('odoo/partners')
  @Permissions('finance.odooExport')
  async odooPartners(@Res() res: Response) {
    const buffer = await this.odooExportService.exportPartners();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="odoo_res_partner.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('odoo/customer-invoices')
  @Permissions('finance.odooExport')
  async odooCustomerInvoices(
    @Query('dateFrom') dateFrom: string | undefined,
    @Query('dateTo') dateTo: string | undefined,
    @Res() res: Response,
  ) {
    const buffer = await this.odooExportService.exportCustomerInvoices(dateFrom, dateTo);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="odoo_customer_invoices.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('odoo/b2c-partners')
  @Permissions('finance.odooExport')
  async odooB2CPartners(
    @Query('dateFrom') dateFrom: string | undefined,
    @Query('dateTo') dateTo: string | undefined,
    @Res() res: Response,
  ) {
    const buffer = await this.odooExportService.exportB2CPartners(dateFrom, dateTo);
    res.set({
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="odoo_b2c_res_partner.csv"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('odoo/b2c-invoices')
  @Permissions('finance.odooExport')
  async odooB2CInvoices(
    @Query('dateFrom') dateFrom: string | undefined,
    @Query('dateTo') dateTo: string | undefined,
    @Res() res: Response,
  ) {
    const buffer = await this.odooExportService.exportB2CCustomerInvoices(dateFrom, dateTo);
    res.set({
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="odoo_b2c_customer_invoices.csv"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('odoo/vendor-bills')
  @Permissions('finance.odooExport')
  async odooVendorBills(
    @Query('dateFrom') dateFrom: string | undefined,
    @Query('dateTo') dateTo: string | undefined,
    @Res() res: Response,
  ) {
    const buffer = await this.odooExportService.exportVendorBills(dateFrom, dateTo);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="odoo_vendor_bills.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('odoo/payments')
  @Permissions('finance.odooExport')
  async odooPayments(
    @Query('dateFrom') dateFrom: string | undefined,
    @Query('dateTo') dateTo: string | undefined,
    @Res() res: Response,
  ) {
    const buffer = await this.odooExportService.exportPayments(dateFrom, dateTo);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="odoo_payments.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('odoo/all-in-one')
  @Permissions('finance.odooExport')
  async odooAllInOne(
    @Query('dateFrom') dateFrom: string | undefined,
    @Query('dateTo') dateTo: string | undefined,
    @Res() res: Response,
  ) {
    const buffer = await this.odooExportService.exportAllInOne(dateFrom, dateTo);
    const date = new Date().toISOString().slice(0, 10);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="odoo_export_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }
}
