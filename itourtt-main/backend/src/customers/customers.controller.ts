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
  ParseUUIDPipe,
  Res,
  UseInterceptors,
  UploadedFile,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import type { Response } from 'express';
import { CustomersService } from './customers.service.js';
import { CreateCustomerDto } from './dto/create-customer.dto.js';
import { UpdateCustomerDto } from './dto/update-customer.dto.js';
import { BulkPriceListDto } from './dto/price-list.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional, IsString } from 'class-validator';

class CustomerListQueryDto extends PaginationDto {
  @IsOptional()
  @IsString()
  search?: string;
}

@Controller('customers')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class CustomersController {
  constructor(private readonly customersService: CustomersService) {}

  @Get()
  @Permissions('customers')
  async findAll(@Query() query: CustomerListQueryDto) {
    const { search, ...pagination } = query;
    return this.customersService.findAll(pagination, search);
  }

  @Get('export/excel')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.export')
  async exportExcel(@Res() res: Response) {
    const buffer = await this.customersService.exportToExcel();
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="customers_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('import/template')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.downloadTemplate')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.customersService.generateImportTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="customers_import_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.import')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.customersService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} customers with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} customers`;
    return new ApiResponse(result, message);
  }

  @Get(':id')
  @Permissions('customers')
  async findOne(@Param('id', ParseUUIDPipe) id: string) {
    const customer = await this.customersService.findOne(id);
    return new ApiResponse(customer);
  }

  @Post()
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.addButton')
  async create(@Body() dto: CreateCustomerDto) {
    const customer = await this.customersService.create(dto);
    return new ApiResponse(customer, 'Customer created successfully');
  }

  @Patch(':id')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.table.editButton')
  async update(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: UpdateCustomerDto,
  ) {
    const customer = await this.customersService.update(id, dto);
    return new ApiResponse(customer, 'Customer updated successfully');
  }

  @Patch(':id/status')
  @Roles('ADMIN')
  @Permissions('customers.table.toggleStatus')
  async toggleStatus(@Param('id', ParseUUIDPipe) id: string) {
    const result = await this.customersService.toggleStatus(id);
    return new ApiResponse(result, 'Customer status updated successfully');
  }

  @Delete('bulk')
  @Roles('ADMIN')
  @Permissions('customers.table.deleteButton')
  async bulkDelete(@Body() dto: { ids: string[] }) {
    const result = await this.customersService.bulkDelete(dto.ids);
    return new ApiResponse(result, `${result.deleted} customers deleted successfully`);
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('customers.table.deleteButton')
  async remove(@Param('id', ParseUUIDPipe) id: string) {
    const result = await this.customersService.remove(id);
    return new ApiResponse(result, 'Customer deleted successfully');
  }

  // Price List Endpoints

  @Get(':id/price-list')
  @Permissions('customers.detail.priceList')
  async getPriceList(@Param('id', ParseUUIDPipe) id: string) {
    const priceItems = await this.customersService.getPriceList(id);
    return new ApiResponse(priceItems);
  }

  @Post(':id/price-list')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.detail.priceList.editPrice')
  async upsertPriceItems(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() dto: BulkPriceListDto,
  ) {
    const result = await this.customersService.upsertPriceItems(id, dto);
    return new ApiResponse(result, 'Price list updated successfully');
  }

  @Delete(':id/price-list/:priceItemId')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.detail.priceList.deleteRoute')
  async deletePriceItem(
    @Param('id', ParseUUIDPipe) id: string,
    @Param('priceItemId', ParseUUIDPipe) priceItemId: string,
  ) {
    const result = await this.customersService.deletePriceItem(id, priceItemId);
    return new ApiResponse(result, 'Price item deleted successfully');
  }

  @Get('price-list/template')
  @Permissions('customers.detail.priceList.downloadTemplate')
  async downloadPriceListTemplate(@Res() res: Response) {
    const buffer = await this.customersService.generatePriceListTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="price-list-template.xlsx"',
      'Content-Length': buffer.length,
    });
    res.send(buffer);
  }

  @Post(':id/price-list/import')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('customers.detail.priceList.import')
  @UseInterceptors(FileInterceptor('file'))
  async importPriceList(
    @Param('id', ParseUUIDPipe) id: string,
    @UploadedFile() file: Express.Multer.File,
  ) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.customersService.importPriceListFromExcel(id, file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} items with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} price items`;
    return new ApiResponse(result, message);
  }
}
