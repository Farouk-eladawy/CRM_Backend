import { Module } from '@nestjs/common';
import { ExtrasController } from './extras.controller.js';
import { ExtrasService } from './extras.service.js';

@Module({
  controllers: [ExtrasController],
  providers: [ExtrasService],
  exports: [ExtrasService],
})
export class ExtrasModule {}
