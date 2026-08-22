import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module.js';
import { PublicPricesModule } from '../public-prices/public-prices.module.js';
import { GuestBookingsModule } from '../guest-bookings/guest-bookings.module.js';
import { PartnerController } from './partner.controller.js';
import { PartnerService } from './partner.service.js';
import { PartnerKeyGuard } from './guards/partner-key.guard.js';

@Module({
  imports: [PrismaModule, PublicPricesModule, GuestBookingsModule],
  controllers: [PartnerController],
  providers: [PartnerService, PartnerKeyGuard],
})
export class PartnerModule {}
