import { Module } from '@nestjs/common';
import { DriverPortalController } from './driver-portal.controller.js';
import { DriverPortalService } from './driver-portal.service.js';
import { NoShowDisputeService } from './no-show-dispute.service.js';
import { SupplierAutoCompleteService } from './supplier-auto-complete.service.js';
import { EmailModule } from '../email/email.module.js';
import { GoogleDriveModule } from '../google-drive/google-drive.module.js';
import { JobCompletionModule } from '../common/services/job-completion.module.js';

@Module({
  imports: [EmailModule, GoogleDriveModule, JobCompletionModule],
  controllers: [DriverPortalController],
  providers: [DriverPortalService, NoShowDisputeService, SupplierAutoCompleteService],
})
export class DriverPortalModule {}
