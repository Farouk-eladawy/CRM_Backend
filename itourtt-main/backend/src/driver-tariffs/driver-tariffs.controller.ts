import {
  Controller,
  Get,
  Post,
  Delete,
  Param,
  Body,
  Query,
  Res,
  UseGuards,
  UseInterceptors,
  UploadedFile,
} from '@nestjs/common';
import type { Response } from 'express';
import { FileInterceptor } from '@nestjs/platform-express';
import { DriverTariffsService } from './driver-tariffs.service.js';
import { UpsertTariffDto } from './dto/upsert-tariff.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional, IsString } from 'class-validator';

class TariffFilterDto {
  @IsOptional() @IsString() fromZoneId?: string;
  @IsOptional() @IsString() toZoneId?: string;
  @IsOptional() @IsString() vehicleTypeId?: string;
}

@Controller('driver-tariffs')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class DriverTariffsController {
  constructor(private readonly driverTariffsService: DriverTariffsService) {}

  @Get()
  @Permissions('driver-tariffs')
  async findAll(@Query() filters: TariffFilterDto) {
    const data = await this.driverTariffsService.findAll(filters);
    return new ApiResponse(data);
  }

  @Get('import/template')
  @Permissions('driver-tariffs')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.driverTariffsService.generateTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="driver_tariffs_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('driver-tariffs.upsert')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.driverTariffsService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} tariffs with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} tariffs`;
    return new ApiResponse(result, message);
  }

  @Post()
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('driver-tariffs.upsert')
  async upsert(@Body() dto: UpsertTariffDto) {
    const data = await this.driverTariffsService.upsert(dto);
    return new ApiResponse(data, 'Driver tariff saved successfully');
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('driver-tariffs.delete')
  async remove(@Param('id') id: string) {
    await this.driverTariffsService.remove(id);
    return new ApiResponse(null, 'Driver tariff deleted successfully');
  }
}
