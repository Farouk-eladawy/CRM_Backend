import { Module } from '@nestjs/common';
import { JobCompletionService } from './job-completion.service.js';
import { DriverTariffsModule } from '../../driver-tariffs/driver-tariffs.module.js';

@Module({
  imports: [DriverTariffsModule],
  providers: [JobCompletionService],
  exports: [JobCompletionService],
})
export class JobCompletionModule {}
