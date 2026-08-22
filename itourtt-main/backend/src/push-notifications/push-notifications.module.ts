import { Module, Global } from '@nestjs/common';
import { PushNotificationsService } from './push-notifications.service.js';

@Global()
@Module({
  providers: [PushNotificationsService],
  exports: [PushNotificationsService],
})
export class PushNotificationsModule {}
