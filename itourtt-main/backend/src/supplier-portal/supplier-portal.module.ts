import { Module } from '@nestjs/common';
import { SupplierPortalController } from './supplier-portal.controller.js';
import { SupplierPortalService } from './supplier-portal.service.js';

@Module({
  controllers: [SupplierPortalController],
  providers: [SupplierPortalService],
})
export class SupplierPortalModule {}
