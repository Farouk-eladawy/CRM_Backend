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
import { FileInterceptor } from '@nestjs/platform-express';
import type { Response } from 'express';
import { diskStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { DriversService } from './drivers.service.js';
import { CreateDriverDto } from './dto/create-driver.dto.js';
import { UpdateDriverDto } from './dto/update-driver.dto.js';
import { AssignVehicleDto } from './dto/assign-vehicle.dto.js';
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

class DriverListQueryDto extends PaginationDto {
  @IsOptional()
  @Transform(({ value }) => (value === undefined ? undefined : value === 'true' || value === true))
  isActive?: boolean;
}

@Controller('drivers')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class DriversController {
  constructor(private readonly driversService: DriversService) {}

  @Get()
  @Permissions('drivers')
  async findAll(@Query() query: DriverListQueryDto) {
    const { isActive, ...pagination } = query;
    return this.driversService.findAll(pagination, isActive);
  }

  @Get('export/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.export')
  async exportExcel(@Res() res: Response) {
    const buffer = await this.driversService.exportToExcel();
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="drivers_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('import/template')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.downloadTemplate')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.driversService.generateImportTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="drivers_import_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.import')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.driversService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} drivers with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} drivers`;
    return new ApiResponse(result, message);
  }

  @Post()
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.addButton')
  async create(@Body() dto: CreateDriverDto) {
    const driver = await this.driversService.create(dto);
    return new ApiResponse(driver, 'Driver created successfully');
  }

  @Get(':id')
  @Permissions('drivers')
  async findOne(@Param('id') id: string) {
    const driver = await this.driversService.findOne(id);
    return new ApiResponse(driver);
  }

  @Patch(':id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.table.editButton')
  async update(
    @Param('id') id: string,
    @Body() dto: UpdateDriverDto,
  ) {
    const driver = await this.driversService.update(id, dto);
    return new ApiResponse(driver, 'Driver updated successfully');
  }

  @Post(':id/vehicles')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.table.editButton')
  async assignVehicle(
    @Param('id') id: string,
    @Body() dto: AssignVehicleDto,
  ) {
    const assignment = await this.driversService.assignVehicle(id, dto);
    return new ApiResponse(assignment, 'Vehicle assigned to driver successfully');
  }

  @Delete(':driverId/vehicles/:vehicleId')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.table.editButton')
  async unassignVehicle(
    @Param('driverId') driverId: string,
    @Param('vehicleId') vehicleId: string,
  ) {
    const result = await this.driversService.unassignVehicle(driverId, vehicleId);
    return new ApiResponse(result, 'Vehicle unassigned from driver successfully');
  }

  @Patch(':id/status')
  @Roles('ADMIN')
  @Permissions('drivers.table.toggleStatus')
  async toggleStatus(@Param('id') id: string) {
    const result = await this.driversService.toggleStatus(id);
    return new ApiResponse(result, 'Driver status updated successfully');
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('drivers.table.deleteButton')
  async softDelete(@Param('id') id: string) {
    await this.driversService.softDelete(id);
    return new ApiResponse(null, 'Driver removed successfully');
  }

  @Post(':id/attachment')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.table.uploadAttachment')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadAttachment(
    @Param('id') id: string,
    @UploadedFile() file: any,
  ) {
    const url = '/uploads/' + file.filename;
    await this.driversService.updateAttachment(id, url);
    return { url };
  }

  @Post(':id/account')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.table.createAccount')
  async createUserAccount(
    @Param('id') id: string,
    @Body() dto: { password: string },
  ) {
    const result = await this.driversService.createUserAccount(id, dto);
    return new ApiResponse(result, 'Driver user account created successfully');
  }

  @Patch(':id/account/password')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('drivers.table.resetPassword')
  async resetPassword(
    @Param('id') id: string,
    @Body() dto: { password: string },
  ) {
    const result = await this.driversService.resetPassword(id, dto.password);
    return new ApiResponse(result, 'Password reset successfully');
  }

  @Get(':id/trip-fees')
  @Permissions('drivers')
  async getTripFees(
    @Param('id', ParseUUIDPipe) id: string,
    @Query('from') from?: string,
    @Query('to') to?: string,
  ) {
    const result = await this.driversService.getTripFees(id, from, to);
    return new ApiResponse(result);
  }
}
