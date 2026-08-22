import { Module } from '@nestjs/common';
import { JobServiceTypesController } from './job-service-types.controller.js';
import { JobServiceTypesService } from './job-service-types.service.js';

@Module({
  controllers: [JobServiceTypesController],
  providers: [JobServiceTypesService],
  exports: [JobServiceTypesService],
})
export class JobServiceTypesModule {}
