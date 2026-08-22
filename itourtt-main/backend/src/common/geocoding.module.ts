import { Module } from '@nestjs/common';
import { GeocodingService } from './geocoding.service.js';
import { SettingsModule } from '../settings/settings.module.js';

@Module({
  imports: [SettingsModule],
  providers: [GeocodingService],
  exports: [GeocodingService],
})
export class GeocodingModule {}
