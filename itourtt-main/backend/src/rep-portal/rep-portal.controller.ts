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
import { RepPortalService } from './rep-portal.service.js';
import { GoogleDriveService, isDriveFileId } from '../google-drive/google-drive.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsString, IsIn, IsOptional, IsNumber, IsInt, Min } from 'class-validator';
import * as path from 'path';
import * as fs from 'fs';
import { stampEvidenceImage, StampMeta } from '../common/utils/stamp-image.js';

// Fallback disk storage (used when Drive is not configured)
const uploadsBase = path.join(process.cwd(), 'uploads');

function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}
ensureDir(path.join(uploadsBase, 'no-show'));
ensureDir(path.join(uploadsBase, 'in-place'));
ensureDir(path.join(uploadsBase, 'completed'));

const memStore = memoryStorage();

class UpdateJobStatusDto {
  @IsString()
  @IsIn(['COMPLETED', 'CANCELLED'])
  status!: string;

  // GPS is mandatory for every status change — never skipped.
  @IsNumber()
  latitude!: number;

  @IsNumber()
  longitude!: number;
}

class DateQueryDto {
  @IsOptional()
  @IsString()
  date?: string;
}

class GuestSurveyDto {
  @IsIn(['20-30', '30-45', '45-60'])
  ageRange!: string;

  @IsInt()
  @Min(0)
  noOfAdults!: number;

  @IsString()
  flightNo!: string;

  @IsInt()
  @Min(0)
  noOfInfants!: number;

  @IsOptional()
  @IsString()
  stayLength?: string;

  @IsIn(['YES', 'NO'])
  repeaterGuest!: string;

  @IsString()
  guestNationality!: string;

  @IsInt()
  @Min(0)
  noOfChildren!: number;

  @IsOptional()
  @IsString()
  localTravelAgent?: string;

  @IsString()
  hotelName!: string;

  @IsOptional()
  @IsString()
  email?: string;

  @IsString()
  generalComment!: string;

  @IsString()
  contactNumber!: string;
}

@Controller('rep-portal')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles('REP')
export class RepPortalController {
  constructor(
    private readonly repPortalService: RepPortalService,
    private readonly googleDriveService: GoogleDriveService,
  ) {}

  @Get('jobs')
  async getMyJobs(
    @CurrentUser('id') userId: string,
    @Query() query: DateQueryDto,
  ) {
    const result = await this.repPortalService.getMyJobs(userId, query.date);
    return new ApiResponse(result);
  }

  @Get('jobs/history')
  async getJobHistory(
    @CurrentUser('id') userId: string,
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
  ) {
    const today = new Date().toISOString().split('T')[0];
    const result = await this.repPortalService.getJobHistory(userId, dateFrom || today, dateTo || today);
    return new ApiResponse(result);
  }

  @Get('jobs/:jobId')
  async getJobDetail(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
  ) {
    const job = await this.repPortalService.findJobDetail(userId, jobId);
    return new ApiResponse(job);
  }

  @Patch('jobs/:jobId/status')
  async updateJobStatus(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() dto: UpdateJobStatusDto,
  ) {
    const result = await this.repPortalService.updateJobStatus(
      userId,
      jobId,
      dto.status as any,
      dto.latitude,
      dto.longitude,
    );
    return new ApiResponse(result, 'Job status updated');
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

    const stampMeta = await this.repPortalService.getJobStampMeta(jobId).catch((e) => { console.error('[stamp] getJobStampMeta failed:', e); return undefined; });
    const imageUrls = await this.uploadFiles(files, jobId, 'no-show', 'no-show', latitude, longitude, stampMeta);

    const result = await this.repPortalService.submitNoShow(userId, jobId, imageUrls, latitude, longitude);
    return new ApiResponse(result, 'No-show evidence submitted');
  }

  @Post('jobs/:jobId/in-place')
  @UseInterceptors(FilesInterceptor('images', 2, { storage: memStore }))
  async submitInPlace(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @UploadedFiles() files: Express.Multer.File[],
    @Body() body: { latitude: string; longitude: string },
  ) {
    if (!files || files.length < 2) {
      throw new BadRequestException('Exactly 2 images are required for in-place evidence');
    }

    // GPS is mandatory: reject the evidence upload when a fix is missing so
    // location is never absent from the audit trail.
    const latitude = parseFloat(body.latitude);
    const longitude = parseFloat(body.longitude);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      throw new BadRequestException('Valid GPS coordinates are required');
    }

    const stampMeta = await this.repPortalService.getJobStampMeta(jobId).catch((e) => { console.error('[stamp] getJobStampMeta failed:', e); return undefined; });
    const imageUrls = await this.uploadFiles(files, jobId, 'rep', 'in-place', latitude, longitude, stampMeta);

    const result = await this.repPortalService.submitInPlace(userId, jobId, imageUrls, latitude, longitude);
    return new ApiResponse(result, 'In-place evidence submitted');
  }

  @Get('jobs/:jobId/survey')
  async getGuestSurvey(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
  ) {
    const result = await this.repPortalService.getGuestSurvey(userId, jobId);
    return new ApiResponse(result);
  }

  @Post('jobs/:jobId/survey')
  async submitGuestSurvey(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() dto: GuestSurveyDto,
  ) {
    const result = await this.repPortalService.submitGuestSurvey(userId, jobId, dto);
    return new ApiResponse(result, 'Guest survey submitted');
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

    const stampMeta = await this.repPortalService.getJobStampMeta(jobId).catch((e) => { console.error('[stamp] getJobStampMeta failed:', e); return undefined; });
    const imageUrls = await this.uploadFiles(files, jobId, 'rep', 'completed', latitude, longitude, stampMeta);

    const result = await this.repPortalService.submitCompleted(userId, jobId, imageUrls, latitude, longitude);
    return new ApiResponse(result, 'Completed evidence submitted');
  }

  @Patch('jobs/:jobId/flight-delay')
  async submitFlightDelay(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() body: { arrivalTime: string },
  ) {
    if (!body.arrivalTime) {
      throw new BadRequestException('New arrival time is required');
    }
    const result = await this.repPortalService.submitFlightDelay(userId, jobId, body.arrivalTime);
    return new ApiResponse(result, 'Flight delay reported successfully');
  }

  @Post('jobs/:jobId/update')
  async submitUpdate(
    @CurrentUser('id') userId: string,
    @Param('jobId') jobId: string,
    @Body() body: { message: string },
  ) {
    if (!body.message || !body.message.trim()) {
      throw new BadRequestException('Message is required');
    }
    const result = await this.repPortalService.submitUpdate(userId, jobId, body.message.trim());
    return new ApiResponse(result, 'Update submitted');
  }

  @Get('notifications')
  async getNotifications(@CurrentUser('id') userId: string) {
    const result = await this.repPortalService.getNotifications(userId);
    return new ApiResponse(result);
  }

  @Patch('notifications/:id/read')
  async markNotificationRead(
    @CurrentUser('id') userId: string,
    @Param('id', ParseUUIDPipe) id: string,
  ) {
    const result = await this.repPortalService.markNotificationRead(userId, id);
    return new ApiResponse(result);
  }

  @Patch('notifications/read-all')
  async markAllRead(@CurrentUser('id') userId: string) {
    const result = await this.repPortalService.markAllRead(userId);
    return new ApiResponse(result);
  }

  @Get('profile')
  async getProfile(@CurrentUser('id') userId: string) {
    const result = await this.repPortalService.getProfile(userId);
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
        // Drive not configured — save to local disk as fallback
        const dir = path.join(uploadsBase, localSubdir);
        const localPath = path.join(dir, uniqueName);
        fs.writeFileSync(localPath, buffer);
        urls.push(`/uploads/${localSubdir}/${uniqueName}`);
      }
    }

    return urls;
  }
}
