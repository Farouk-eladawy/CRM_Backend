import { Module } from '@nestjs/common';
import { PublicPricesController } from './public-prices.controller.js';
import { PublicPricesService } from './public-prices.service.js';

@Module({
  controllers: [PublicPricesController],
  providers: [PublicPricesService],
  exports: [PublicPricesService],
})
export class PublicPricesModule {}
