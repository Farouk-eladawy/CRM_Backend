import { Module } from '@nestjs/common';
import { TrafficJobsController } from './traffic-jobs.controller.js';
import { TrafficJobsService } from './traffic-jobs.service.js';
import { NotificationsModule } from '../notifications/notifications.module.js';
import { WhatsappNotificationsModule } from '../whatsapp-notifications/whatsapp-notifications.module.js';
import { SettingsModule } from '../settings/settings.module.js';
import { DriverTariffsModule } from '../driver-tariffs/driver-tariffs.module.js';
import { GoogleDriveModule } from '../google-drive/google-drive.module.js';
import { JobCompletionModule } from '../common/services/job-completion.module.js';

@Module({
  imports: [NotificationsModule, WhatsappNotificationsModule, SettingsModule, DriverTariffsModule, GoogleDriveModule, JobCompletionModule],
  controllers: [TrafficJobsController],
  providers: [TrafficJobsService],
  exports: [TrafficJobsService],
})
export class TrafficJobsModule {}
