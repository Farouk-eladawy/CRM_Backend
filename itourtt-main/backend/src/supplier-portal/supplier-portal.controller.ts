import {
  Controller,
  Get,
  Patch,
  Param,
  Body,
  Query,
  UseGuards,
} from '@nestjs/common';
import { SupplierPortalService } from './supplier-portal.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional, IsString } from 'class-validator';

class DateQueryDto {
  @IsOptional()
  @IsString()
  date?: string;
}

class CompleteJobDto {
  @IsOptional()
  @IsString()
  notes?: string;
}

@Controller('supplier-portal')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles('SUPPLIER')
export class SupplierPortalController {
  constructor(private readonly supplierPortalService: SupplierPortalService) {}

  @Get('jobs')
  async getMyJobs(
    @CurrentUser('id') userId: string,
    @Query() query: DateQueryDto,
  ) {
    const result = await this.supplierPortalService.getMyJobs(userId, query.date);
    return new ApiResponse(result);
  }

  @Get('jobs/:jobId')
  async getJobDetail(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
  ) {
    const job = await this.supplierPortalService.findJobDetail(userId, jobId);
    return new ApiResponse(job);
  }

  @Patch('jobs/:jobId/complete')
  async completeJob(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() dto: CompleteJobDto,
  ) {
    const result = await this.supplierPortalService.completeJob(userId, jobId, dto.notes);
    return new ApiResponse(result, 'Job marked as completed');
  }

  @Get('profile')
  async getProfile(@CurrentUser('id') userId: string) {
    const result = await this.supplierPortalService.getProfile(userId);
    return new ApiResponse(result);
  }
}
