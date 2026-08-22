import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module.js';
import { ContactMessagesService } from './contact-messages.service.js';
import { ContactMessagesAdminController } from './contact-messages.admin.controller.js';

@Module({
  imports: [PrismaModule],
  controllers: [ContactMessagesAdminController],
  providers: [ContactMessagesService],
})
export class ContactMessagesModule {}
