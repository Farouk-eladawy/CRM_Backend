import { Module } from '@nestjs/common';
import { DriverTariffsController } from './driver-tariffs.controller.js';
import { DriverTariffsService } from './driver-tariffs.service.js';

@Module({
  controllers: [DriverTariffsController],
  providers: [DriverTariffsService],
  exports: [DriverTariffsService],
})
export class DriverTariffsModule {}
