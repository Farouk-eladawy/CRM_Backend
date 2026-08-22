import { Module } from '@nestjs/common';
import { WhatsappNotificationsService } from './whatsapp-notifications.service.js';
import { WhatsappNotificationsController } from './whatsapp-notifications.controller.js';

@Module({
  controllers: [WhatsappNotificationsController],
  providers: [WhatsappNotificationsService],
  exports: [WhatsappNotificationsService],
})
export class WhatsappNotificationsModule {}
