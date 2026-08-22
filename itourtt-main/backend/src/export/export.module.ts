import { Module } from '@nestjs/common';
import { ExportController } from './export.controller.js';
import { ExportService } from './export.service.js';
import { GoogleDriveModule } from '../google-drive/google-drive.module.js';

@Module({
  imports: [GoogleDriveModule],
  controllers: [ExportController],
  providers: [ExportService],
  exports: [ExportService],
})
export class ExportModule {}
