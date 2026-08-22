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
  Res,
} from '@nestjs/common';
import type { Response } from 'express';
import { PublicPricesService } from './public-prices.service.js';
import { UpsertPublicPricesDto, PublicPriceItemDto } from './dto/upsert-public-prices.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional, IsString } from 'class-validator';

class PublicPriceFilterDto {
  @IsOptional() @IsString() serviceType?: string;
  @IsOptional() @IsString() transferType?: string;
  @IsOptional() @IsString() fromZoneId?: string;
  @IsOptional() @IsString() toZoneId?: string;
  @IsOptional() @IsString() vehicleTypeId?: string;
}

@Controller('public-prices')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class PublicPricesController {
  constructor(private readonly publicPricesService: PublicPricesService) {}

  @Get()
  @Permissions('public-prices')
  async findAll(@Query() filters: PublicPriceFilterDto) {
    const data = await this.publicPricesService.findAll(filters);
    return new ApiResponse(data);
  }

  @Get('export/template')
  @Permissions('public-prices')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.publicPricesService.buildImportTemplate();
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', 'attachment; filename="public_prices_template.xlsx"');
    res.end(buffer);
  }

  @Post('bulk')
  @Permissions('public-prices.bulk')
  @Roles('ADMIN')
  async bulkUpsert(@Body() dto: UpsertPublicPricesDto) {
    const data = await this.publicPricesService.bulkUpsert(dto);
    return new ApiResponse(data, 'Public prices upserted successfully');
  }

  @Patch(':id')
  @Permissions('public-prices.bulk')
  @Roles('ADMIN')
  async updateOne(@Param('id') id: string, @Body() dto: Partial<PublicPriceItemDto>) {
    const data = await this.publicPricesService.updateOne(id, dto);
    return new ApiResponse(data, 'Public price updated');
  }

  @Delete(':id')
  @Permissions('public-prices.delete')
  @Roles('ADMIN')
  async remove(@Param('id') id: string) {
    await this.publicPricesService.remove(id);
    return new ApiResponse(null, 'Public price item deleted successfully');
  }
}
