import { Module } from '@nestjs/common';
import { FinanceController } from './finance.controller.js';
import { FinanceService } from './finance.service.js';
import { InvoiceExportService } from './invoice-export.service.js';
import { OdooExportService } from './odoo-export.service.js';
import { InvoiceSchedulerService } from './invoice-scheduler.service.js';
import { B2CModule } from '../b2c/b2c.module.js';

@Module({
  imports: [B2CModule],
  controllers: [FinanceController],
  providers: [FinanceService, InvoiceExportService, OdooExportService, InvoiceSchedulerService],
  exports: [FinanceService],
})
export class FinanceModule {}
