import {
  Controller, Get, Post, Patch, Delete,
  Body, Param, Res, UseGuards, UseInterceptors, UploadedFile,
} from '@nestjs/common';
import type { Response } from 'express';
import { FileInterceptor } from '@nestjs/platform-express';
import { JobServiceTypesService } from './job-service-types.service.js';
import { CreateJobServiceTypeDto } from './dto/create-job-service-type.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

@Controller('job-service-types')
@UseGuards(JwtAuthGuard, PermissionsGuard)
export class JobServiceTypesController {
  constructor(private readonly service: JobServiceTypesService) {}

  @Get()
  @Permissions('driver-tariffs')
  async findAll() {
    return new ApiResponse(await this.service.findAll());
  }

  @Get('import/template')
  @Permissions('driver-tariffs')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.service.generateTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="service_types_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Permissions('driver-tariffs.upsert')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    const result = await this.service.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} service types with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} service types`;
    return new ApiResponse(result, message);
  }

  @Post()
  @Permissions('driver-tariffs.upsert')
  async create(@Body() dto: CreateJobServiceTypeDto) {
    return new ApiResponse(await this.service.create(dto), 'Service type created');
  }

  @Patch(':id')
  @Permissions('driver-tariffs.upsert')
  async update(@Param('id') id: string, @Body() dto: Partial<CreateJobServiceTypeDto>) {
    return new ApiResponse(await this.service.update(id, dto), 'Service type updated');
  }

  @Delete(':id')
  @Permissions('driver-tariffs.delete')
  async remove(@Param('id') id: string) {
    await this.service.remove(id);
    return new ApiResponse(null, 'Service type deleted');
  }
}
