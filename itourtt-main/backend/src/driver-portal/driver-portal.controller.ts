import {
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Body,
  Query,
  UseGuards,
  UseInterceptors,
  UploadedFiles,
  ParseUUIDPipe,
  BadRequestException,
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { DriverPortalService } from './driver-portal.service.js';
import { GoogleDriveService } from '../google-drive/google-drive.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsString, IsIn, IsOptional, IsNumber, IsBoolean } from 'class-validator';
import { stampEvidenceImage, StampMeta } from '../common/utils/stamp-image.js';

const uploadsDir = path.join(process.cwd(), 'uploads', 'no-show');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}
const completedUploadsDir = path.join(process.cwd(), 'uploads', 'completed');
if (!fs.existsSync(completedUploadsDir)) {
  fs.mkdirSync(completedUploadsDir, { recursive: true });
}
const inProgressUploadsDir = path.join(process.cwd(), 'uploads', 'in-progress');
if (!fs.existsSync(inProgressUploadsDir)) {
  fs.mkdirSync(inProgressUploadsDir, { recursive: true });
}

const memStore = memoryStorage();

class UpdateJobStatusDto {
  @IsString()
  @IsIn(['IN_PROGRESS', 'COMPLETED', 'CANCELLED'])
  status!: string;

  // GPS is mandatory for every status change — never skipped.
  @IsNumber()
  latitude!: number;

  @IsNumber()
  longitude!: number;
}

class MarkCollectedDto {
  @IsBoolean()
  collected!: boolean;
}

class DateQueryDto {
  @IsOptional()
  @IsString()
  date?: string;
}

@Controller('driver-portal')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles('DRIVER')
export class DriverPortalController {
  constructor(
    private readonly driverPortalService: DriverPortalService,
    private readonly googleDriveService: GoogleDriveService,
  ) {}

  @Get('jobs')
  async getMyJobs(
    @CurrentUser('id') userId: string,
    @Query() query: DateQueryDto,
  ) {
    const result = await this.driverPortalService.getMyJobs(userId, query.date);
    return new ApiResponse(result);
  }

  @Get('jobs/history')
  async getJobHistory(
    @CurrentUser('id') userId: string,
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
  ) {
    const today = new Date().toISOString().split('T')[0];
    const result = await this.driverPortalService.getJobHistory(
      userId,
      dateFrom || today,
      dateTo || today,
    );
    return new ApiResponse(result);
  }

  @Get('jobs/:jobId')
  async getJobDetail(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
  ) {
    const job = await this.driverPortalService.findJobDetail(userId, jobId);
    return new ApiResponse(job);
  }

  @Patch('jobs/:jobId/status')
  async updateJobStatus(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() dto: UpdateJobStatusDto,
  ) {
    const result = await this.driverPortalService.updateJobStatus(
      userId,
      jobId,
      dto.status as any,
      dto.latitude,
      dto.longitude,
    );
    return new ApiResponse(result, 'Job status updated');
  }

  @Patch('jobs/:jobId/collection')
  async markCollected(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() dto: MarkCollectedDto,
  ) {
    const result = await this.driverPortalService.markCollected(userId, jobId, dto.collected);
    return new ApiResponse(result, 'Collection status updated');
  }

  @Post('jobs/:jobId/no-show')
  @UseInterceptors(FilesInterceptor('images', 10, { storage: memStore }))
  async submitNoShow(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @UploadedFiles() files: Express.Multer.File[],
    @Body() body: { latitude: string; longitude: string },
  ) {
    if (!files || files.length < 1) {
      throw new BadRequestException('At least one image is required for no-show evidence');
    }

    // GPS is mandatory: reject the evidence upload when a fix is missing so
    // location is never absent from the audit trail.
    const latitude = parseFloat(body.latitude);
    const longitude = parseFloat(body.longitude);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      throw new BadRequestException('Valid GPS coordinates are required');
    }

    const stampMeta = await this.driverPortalService.getJobStampMeta(jobId).catch((e) => { console.error('[stamp] getJobStampMeta failed:', e); return undefined; });
    const imageUrls = await this.uploadFiles(files, jobId, 'no-show', 'no-show', latitude, longitude, stampMeta);

    const result = await this.driverPortalService.submitNoShow(userId, jobId, imageUrls, latitude, longitude);
    return new ApiResponse(result, 'No-show evidence submitted');
  }

  @Post('jobs/:jobId/in-progress')
  @UseInterceptors(FilesInterceptor('images', 10, { storage: memStore }))
  async submitInProgress(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @UploadedFiles() files: Express.Multer.File[],
    @Body() body: { latitude: string; longitude: string },
  ) {
    if (!files || files.length < 1) {
      throw new BadRequestException('At least one image is required for in-progress evidence');
    }

    // GPS is mandatory: reject the evidence upload when a fix is missing so
    // location is never absent from the audit trail.
    const latitude = parseFloat(body.latitude);
    const longitude = parseFloat(body.longitude);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      throw new BadRequestException('Valid GPS coordinates are required');
    }

    const stampMeta = await this.driverPortalService.getJobStampMeta(jobId).catch((e) => { console.error('[stamp] getJobStampMeta failed:', e); return undefined; });
    const imageUrls = await this.uploadFiles(files, jobId, 'driver', 'in-progress', latitude, longitude, stampMeta);

    const result = await this.driverPortalService.submitInProgress(userId, jobId, imageUrls, latitude, longitude);
    return new ApiResponse(result, 'In-progress evidence submitted');
  }

  @Post('jobs/:jobId/completed')
  @UseInterceptors(FilesInterceptor('images', 10, { storage: memStore }))
  async submitCompleted(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @UploadedFiles() files: Express.Multer.File[],
    @Body() body: { latitude: string; longitude: string },
  ) {
    if (!files || files.length < 1) {
      throw new BadRequestException('At least one image is required for completed evidence');
    }

    // GPS is mandatory: reject the evidence upload when a fix is missing so
    // location is never absent from the audit trail.
    const latitude = parseFloat(body.latitude);
    const longitude = parseFloat(body.longitude);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      throw new BadRequestException('Valid GPS coordinates are required');
    }

    const stampMeta = await this.driverPortalService.getJobStampMeta(jobId).catch((e) => { console.error('[stamp] getJobStampMeta failed:', e); return undefined; });
    const imageUrls = await this.uploadFiles(files, jobId, 'driver', 'completed', latitude, longitude, stampMeta);

    const result = await this.driverPortalService.submitCompleted(userId, jobId, imageUrls, latitude, longitude);
    return new ApiResponse(result, 'Completed evidence submitted');
  }

  @Get('notifications')
  async getNotifications(@CurrentUser('id') userId: string) {
    const result = await this.driverPortalService.getNotifications(userId);
    return new ApiResponse(result);
  }

  @Patch('notifications/:id/read')
  async markNotificationRead(
    @CurrentUser('id') userId: string,
    @Param('id', ParseUUIDPipe) id: string,
  ) {
    const result = await this.driverPortalService.markNotificationRead(userId, id);
    return new ApiResponse(result);
  }

  @Patch('notifications/read-all')
  async markAllRead(@CurrentUser('id') userId: string) {
    const result = await this.driverPortalService.markAllRead(userId);
    return new ApiResponse(result);
  }

  @Get('profile')
  async getProfile(@CurrentUser('id') userId: string) {
    const result = await this.driverPortalService.getProfile(userId);
    return new ApiResponse(result);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Upload helper — tries Drive first, falls back to local disk
  // ──────────────────────────────────────────────────────────────────────────

  private async uploadFiles(
    files: Express.Multer.File[],
    jobId: string,
    driveType: 'rep' | 'driver' | 'no-show',
    localSubdir: string,
    lat?: number | null,
    lng?: number | null,
    meta?: StampMeta,
  ): Promise<string[]> {
    const urls: string[] = [];
    const uploadsBase = path.join(process.cwd(), 'uploads');

    for (const file of files) {
      // Always stamp: date/time + rep/driver/status are burned in even when no
      // GPS fix was captured (the GPS line reads "Not captured"). Skipping the
      // stamp on null coords would drop all evidence metadata, not just GPS.
      const buffer = await stampEvidenceImage(file.buffer, lat, lng, undefined, meta).catch(
        () => file.buffer,
      );

      const uniqueName = Date.now() + '-' + file.originalname.replace(/\.[^.]+$/, '') + '.jpg';
      const mimeType = 'image/jpeg';

      const driveId = await this.googleDriveService.uploadFile(
        buffer,
        uniqueName,
        mimeType,
        jobId,
        driveType,
      );

      if (driveId) {
        urls.push(driveId);
      } else {
        const dir = path.join(uploadsBase, localSubdir);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        const localPath = path.join(dir, uniqueName);
        fs.writeFileSync(localPath, buffer);
        urls.push(`/uploads/${localSubdir}/${uniqueName}`);
      }
    }

    return urls;
  }
}
