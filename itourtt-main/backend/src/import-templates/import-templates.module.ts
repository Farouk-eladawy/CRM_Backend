import { Module } from '@nestjs/common';
import { ImportTemplatesController } from './import-templates.controller.js';
import { ImportTemplatesService } from './import-templates.service.js';

@Module({
  controllers: [ImportTemplatesController],
  providers: [ImportTemplatesService],
  exports: [ImportTemplatesService],
})
export class ImportTemplatesModule {}
