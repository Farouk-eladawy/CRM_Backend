import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  Query,
  UseGuards,
  UseInterceptors,
  UploadedFiles,
  BadRequestException,
  ParseUUIDPipe,
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { TrafficJobsService } from './traffic-jobs.service.js';
import { GoogleDriveService } from '../google-drive/google-drive.service.js';
import { CreateJobDto } from './dto/create-job.dto.js';
import { BulkCreateJobsDto } from './dto/bulk-create-jobs.dto.js';
import { JobFilterDto } from './dto/job-filter.dto.js';
import { UpdateJobDto } from './dto/update-job.dto.js';
import { UpdateStatusDto } from './dto/update-status.dto.js';
import { ForceControlDto } from './dto/force-control.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

const memStore = memoryStorage();

@Controller('traffic-jobs')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class TrafficJobsController {
  constructor(
    private readonly trafficJobsService: TrafficJobsService,
    private readonly googleDriveService: GoogleDriveService,
  ) {}

  @Get()
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs')
  async findAll(@Query() filter: JobFilterDto) {
    return this.trafficJobsService.findAll(filter);
  }

  @Get(':id')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs')
  async findOne(@Param('id') id: string) {
    const job = await this.trafficJobsService.findOne(id);
    return new ApiResponse(job);
  }

  @Post('bulk')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs.b2b.importJobs')
  async bulkCreate(
    @Body() dto: BulkCreateJobsDto,
    @CurrentUser('id') userId: string,
  ) {
    const results = await this.trafficJobsService.bulkCreate(dto.jobs, userId);
    return new ApiResponse(results, `Created ${results.created} jobs`);
  }

  @Post()
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs.online.createJob')
  async create(
    @Body() dto: CreateJobDto,
    @CurrentUser('id') userId: string,
  ) {
    const job = await this.trafficJobsService.create(dto, userId);
    return new ApiResponse(job, 'Traffic job created successfully');
  }

  @Patch(':id')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs.online.createJob')
  async update(
    @Param('id') id: string,
    @Body() dto: UpdateJobDto,
    @CurrentUser('id') userId: string,
    @CurrentUser('role') userRole: string,
  ) {
    const job = await this.trafficJobsService.update(id, dto, userId, userRole);
    return new ApiResponse(job, 'Traffic job updated successfully');
  }

  @Patch(':id/status')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs.online.table.statusFilter')
  async updateStatus(
    @Param('id') id: string,
    @Body() dto: UpdateStatusDto,
    @CurrentUser('id') userId: string,
  ) {
    const job = await this.trafficJobsService.updateStatus(id, dto, userId);
    return new ApiResponse(job, 'Traffic job status updated successfully');
  }

  @Patch(':id/control')
  @Permissions('job-control')
  async forceControl(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: ForceControlDto,
  ) {
    const job = await this.trafficJobsService.forceControl(id, dto);
    return new ApiResponse(job, 'Job control updated successfully');
  }

  @Delete(':id')
  @Roles('ADMIN', 'MANAGER', 'DISPATCHER')
  @Permissions('traffic-jobs.online.createJob')
  async remove(@Param('id') id: string) {
    const result = await this.trafficJobsService.remove(id);
    return new ApiResponse(result, 'Traffic job deleted successfully');
  }

  @Post(':id/upload-evidence')
  @Roles('ADMIN')
  @UseInterceptors(FilesInterceptor('images', 10, { storage: memStore }))
  async uploadEvidence(
    @Param('id', ParseUUIDPipe) id: string,
    @UploadedFiles() files: Express.Multer.File[],
    @Body('type') type: string,
    @CurrentUser('id') userId: string,
  ) {
    if (!files?.length) throw new BadRequestException('At least one image is required');
    if (type !== 'driver' && type !== 'rep') throw new BadRequestException('type must be driver or rep');

    const urls: string[] = [];
    const uploadsBase = path.join(process.cwd(), 'uploads');
    for (const file of files) {
      const uniqueName = `${Date.now()}-${file.originalname.replace(/\.[^.]+$/, '')}.jpg`;
      const driveId = await this.googleDriveService.uploadFile(
        file.buffer,
        uniqueName,
        'image/jpeg',
        id,
        type as 'driver' | 'rep',
      );
      if (driveId) {
        urls.push(driveId);
      } else {
        const subdir = type === 'driver' ? 'completed' : 'rep-completed';
        const dir = path.join(uploadsBase, subdir);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(path.join(dir, uniqueName), file.buffer);
        urls.push(`/uploads/${subdir}/${uniqueName}`);
      }
    }

    const result = await this.trafficJobsService.uploadEvidence(id, type as 'driver' | 'rep', urls, userId);
    return new ApiResponse(result, 'Evidence uploaded successfully');
  }

  @Post('recalculate-driver-fees')
  @Roles('ADMIN')
  @Permissions('traffic-jobs')
  async recalculateDriverFees(
    @Body() body: { from: string; to: string },
  ) {
    const result = await this.trafficJobsService.recalculateDriverFees(body.from, body.to);
    return new ApiResponse(result, `Created ${result.created} fee records, skipped ${result.skipped}`);
  }
}
