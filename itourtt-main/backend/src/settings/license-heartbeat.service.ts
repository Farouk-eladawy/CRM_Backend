import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { SettingsService } from './settings.service.js';

// Background heartbeat so revocation/renewals land even when nobody polls the UI.
// checkLicense() throttles the actual network call to ~daily, so a 6-hour cron is cheap.
@Injectable()
export class LicenseHeartbeatService {
  private readonly log = new Logger('LicenseHeartbeat');

  constructor(private readonly settings: SettingsService) {}

  @Cron(CronExpression.EVERY_6_HOURS)
  async beat(): Promise<void> {
    try {
      const s = await this.settings.getLicenseStatus();
      this.log.log(`license: ${s.message}`);
    } catch (e) {
      this.log.warn(`heartbeat failed: ${String(e)}`);
    }
  }
}
