import { Module } from '@nestjs/common';
import { RepsController } from './reps.controller.js';
import { RepsService } from './reps.service.js';

@Module({
  controllers: [RepsController],
  providers: [RepsService],
  exports: [RepsService],
})
export class RepsModule {}
