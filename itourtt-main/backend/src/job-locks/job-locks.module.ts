import { Module } from '@nestjs/common';
import { JobLocksController } from './job-locks.controller.js';
import { JobLocksService } from './job-locks.service.js';

@Module({
  controllers: [JobLocksController],
  providers: [JobLocksService],
})
export class JobLocksModule {}
