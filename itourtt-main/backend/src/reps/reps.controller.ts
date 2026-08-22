import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  Query,
  Res,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  ParseUUIDPipe,
} from '@nestjs/common';
import type { Response } from 'express';
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { RepsService } from './reps.service.js';
import { CreateRepDto } from './dto/create-rep.dto.js';
import { UpdateRepDto } from './dto/update-rep.dto.js';
import { AssignZoneDto } from './dto/assign-zone.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional } from 'class-validator';
import { Transform } from 'class-transformer';

const uploadsDir = path.join(process.cwd(), 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const uploadStorage = diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (_req, file, cb) => {
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  },
});

class RepListQueryDto extends PaginationDto {
  @IsOptional()
  @Transform(({ value }) => (value === undefined ? undefined : value === 'true' || value === true))
  isActive?: boolean;
}

@Controller('reps')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class RepsController {
  constructor(private readonly repsService: RepsService) {}

  @Get()
  @Permissions('reps')
  async findAll(@Query() query: RepListQueryDto) {
    const { isActive, ...pagination } = query;
    return this.repsService.findAll(pagination, isActive);
  }

  @Get('export/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.export')
  async exportExcel(@Res() res: Response) {
    const buffer = await this.repsService.exportToExcel();
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="reps_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('import/template')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.downloadTemplate')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.repsService.generateImportTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="reps_import_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.import')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.repsService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} reps with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} reps`;
    return new ApiResponse(result, message);
  }

  @Post()
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.addButton')
  async create(@Body() dto: CreateRepDto) {
    const rep = await this.repsService.create(dto);
    return new ApiResponse(rep, 'Rep created successfully');
  }

  @Get(':id')
  @Permissions('reps')
  async findOne(@Param('id') id: string) {
    const rep = await this.repsService.findOne(id);
    return new ApiResponse(rep);
  }

  @Patch(':id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.table.editButton')
  async update(
    @Param('id') id: string,
    @Body() dto: UpdateRepDto,
  ) {
    const rep = await this.repsService.update(id, dto);
    return new ApiResponse(rep, 'Rep updated successfully');
  }

  @Patch(':id/status')
  @Roles('ADMIN')
  @Permissions('reps.table.toggleStatus')
  async toggleStatus(@Param('id') id: string) {
    const result = await this.repsService.toggleStatus(id);
    return new ApiResponse(result, 'Rep status updated successfully');
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('reps.table.deleteButton')
  async softDelete(@Param('id') id: string) {
    const result = await this.repsService.softDelete(id);
    return new ApiResponse(result, 'Rep removed successfully');
  }

  @Post(':id/zones')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.table.editButton')
  async assignZone(
    @Param('id') id: string,
    @Body() dto: AssignZoneDto,
  ) {
    const assignment = await this.repsService.assignZone(id, dto);
    return new ApiResponse(assignment, 'Zone assigned to rep successfully');
  }

  @Delete(':repId/zones/:zoneId')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.table.editButton')
  async unassignZone(
    @Param('repId') repId: string,
    @Param('zoneId') zoneId: string,
  ) {
    const result = await this.repsService.unassignZone(repId, zoneId);
    return new ApiResponse(result, 'Zone unassigned from rep successfully');
  }

  @Post(':id/attachment')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('reps.table.uploadAttachment')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadAttachment(
    @Param('id') id: string,
    @UploadedFile() file: any,
  ) {
    const url = '/uploads/' + file.filename;
    await this.repsService.updateAttachment(id, url);
    return { url };
  }

  @Post(':id/account')
  @Roles('ADMIN')
  @Permissions('reps.table.createAccount')
  async createAccount(
    @Param('id') id: string,
    @Body() dto: { password: string },
  ) {
    const result = await this.repsService.createUserAccount(id, dto);
    return new ApiResponse(result, 'Rep account created successfully');
  }

  @Patch(':id/account/password')
  @Roles('ADMIN')
  @Permissions('reps.table.resetPassword')
  async resetPassword(
    @Param('id') id: string,
    @Body() dto: { password: string },
  ) {
    const result = await this.repsService.resetPassword(id, dto.password);
    return new ApiResponse(result, 'Password reset successfully');
  }

  @Get(':id/fees')
  @Permissions('reps')
  async getFees(
    @Param('id', ParseUUIDPipe) id: string,
    @Query('from') from?: string,
    @Query('to') to?: string,
  ) {
    const result = await this.repsService.getFees(id, from, to);
    return new ApiResponse(result);
  }
}
