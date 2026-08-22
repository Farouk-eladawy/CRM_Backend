import {
  Body,
  Controller,
  Get,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';
import { Public } from '../common/decorators/public.decorator.js';
import { PartnerKeyGuard } from './guards/partner-key.guard.js';
import { PartnerService } from './partner.service.js';
import { PartnerJobDto } from './dto/partner-job.dto.js';
import { UpsertPublicPricesDto } from '../public-prices/dto/upsert-public-prices.dto.js';

/**
 * The iTourTT ↔ B2C seam. See PARTNER-API-CONTRACT.md in the B2C repo.
 * `@Public()` bypasses the global JwtAuthGuard; PartnerKeyGuard enforces the
 * X-Partner-Key service key instead. Agency never touches these — B2C backend does.
 */
@Public()
@UseGuards(PartnerKeyGuard)
@Controller('partner')
export class PartnerController {
  constructor(private readonly partnerService: PartnerService) {}

  @Get('reference')
  getReference() {
    return this.partnerService.getReference();
  }

  @Post('pricing')
  pushPricing(@Body() dto: UpsertPublicPricesDto) {
    return this.partnerService.pushPricing(dto);
  }

  @Post('jobs')
  createJob(@Body() dto: PartnerJobDto) {
    return this.partnerService.createJob(dto);
  }

  @Get('jobs')
  getJobStatuses(@Query('refs') refs?: string) {
    const list = (refs ?? '')
      .split(',')
      .map((r) => r.trim())
      .filter(Boolean);
    return this.partnerService.getJobStatuses(list);
  }
}
