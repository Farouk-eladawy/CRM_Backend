import {
  Controller,
  Get,
  Post,
  Put,
  Patch,
  Delete,
  Body,
  Param,
  Query,
  Res,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  ParseUUIDPipe,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import type { Response } from 'express';
import { SuppliersService } from './suppliers.service.js';
import { CreateSupplierDto } from './dto/create-supplier.dto.js';
import { UpdateSupplierDto } from './dto/update-supplier.dto.js';
import { CreateTripPriceDto } from './dto/create-trip-price.dto.js';
import { CreateSupplierVehicleDto, UpdateSupplierVehicleDto } from './dto/create-vehicle.dto.js';
import { CreateSupplierDriverDto, UpdateSupplierDriverDto } from './dto/create-driver.dto.js';
import { BulkPriceListDto } from './dto/supplier-price-list.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

@Controller('suppliers')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class SuppliersController {
  constructor(private readonly suppliersService: SuppliersService) {}

  @Get()
  @Permissions('suppliers')
  async findAll(
    @Query() pagination: PaginationDto,
    @Query('isActive') isActive?: string,
  ) {
    const page = pagination.page ?? 1;
    const limit = pagination.limit ?? 20;
    const active =
      isActive === 'true' ? true : isActive === 'false' ? false : undefined;

    return this.suppliersService.findAll(page, limit, active);
  }

  @Get('export/excel')
  @Roles('ADMIN')
  @Permissions('suppliers.export')
  async exportExcel(@Res() res: Response) {
    const buffer = await this.suppliersService.exportToExcel();
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="suppliers_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('import/template')
  @Roles('ADMIN')
  @Permissions('suppliers.downloadTemplate')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.suppliersService.generateImportTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="suppliers_import_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN')
  @Permissions('suppliers.import')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.suppliersService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} suppliers with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} suppliers`;
    return new ApiResponse(result, message);
  }

  @Post()
  @Roles('ADMIN')
  @Permissions('suppliers.addButton')
  async create(@Body() dto: CreateSupplierDto) {
    return this.suppliersService.create(dto);
  }

  @Get(':id')
  @Permissions('suppliers')
  async findOne(@Param('id') id: string) {
    return this.suppliersService.findOne(id);
  }

  @Put(':id')
  @Permissions('suppliers.table.editButton')
  async update(
    @Param('id') id: string,
    @Body() dto: UpdateSupplierDto,
  ) {
    return this.suppliersService.update(id, dto);
  }

  @Patch(':id/status')
  @Roles('ADMIN')
  @Permissions('suppliers.table.toggleStatus')
  async toggleStatus(@Param('id') id: string) {
    const result = await this.suppliersService.toggleStatus(id);
    return new ApiResponse(result, 'Supplier status updated successfully');
  }

  @Delete('bulk')
  @Roles('ADMIN')
  @Permissions('suppliers.table.deleteButton')
  async bulkDelete(@Body() dto: { ids: string[] }) {
    const result = await this.suppliersService.bulkDelete(dto.ids);
    return new ApiResponse(result, `${result.deleted} suppliers deleted successfully`);
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('suppliers.table.deleteButton')
  async delete(@Param('id') id: string) {
    await this.suppliersService.delete(id);
    return new ApiResponse(null, 'Supplier deleted successfully');
  }

  // ─── Trip Prices (legacy) ──────────────────────────────

  @Post(':id/trip-prices')
  @Permissions('suppliers')
  async createTripPrice(
    @Param('id') id: string,
    @Body() dto: CreateTripPriceDto,
  ) {
    return this.suppliersService.createTripPrice(id, dto);
  }

  @Get(':id/trip-prices')
  @Permissions('suppliers')
  async findTripPrices(@Param('id') id: string) {
    return this.suppliersService.findTripPrices(id);
  }

  @Put('trip-prices/:priceId')
  @Permissions('suppliers')
  async updateTripPrice(
    @Param('priceId') priceId: string,
    @Body() dto: CreateTripPriceDto,
  ) {
    return this.suppliersService.updateTripPrice(priceId, dto);
  }

  // ─── Vehicles (Supplier-scoped) ───────────────────────

  @Get(':id/vehicles')
  @Permissions('suppliers')
  async findVehicles(
    @Param('id') id: string,
    @Query() pagination: PaginationDto,
    @Query('vehicleTypeId') vehicleTypeId?: string,
  ) {
    const page = pagination.page ?? 1;
    const limit = pagination.limit ?? 50;
    const result = await this.suppliersService.findVehicles(id, page, limit, vehicleTypeId);
    return new ApiResponse(result);
  }

  @Post(':id/vehicles')
  @Permissions('suppliers')
  async createVehicle(
    @Param('id') id: string,
    @Body() dto: CreateSupplierVehicleDto,
  ) {
    const result = await this.suppliersService.createVehicle(id, dto);
    return new ApiResponse(result, 'Vehicle added successfully');
  }

  @Put(':id/vehicles/:vehicleId')
  @Permissions('suppliers')
  async updateVehicle(
    @Param('id') id: string,
    @Param('vehicleId') vehicleId: string,
    @Body() dto: UpdateSupplierVehicleDto,
  ) {
    const result = await this.suppliersService.updateVehicle(id, vehicleId, dto);
    return new ApiResponse(result, 'Vehicle updated successfully');
  }

  @Delete(':id/vehicles/:vehicleId')
  @Permissions('suppliers')
  async deleteVehicle(
    @Param('id') id: string,
    @Param('vehicleId') vehicleId: string,
  ) {
    await this.suppliersService.deleteVehicle(id, vehicleId);
    return new ApiResponse(null, 'Vehicle removed successfully');
  }

  @Patch(':id/vehicles/:vehicleId/status')
  @Permissions('suppliers')
  async toggleVehicleStatus(
    @Param('id') id: string,
    @Param('vehicleId') vehicleId: string,
  ) {
    const result = await this.suppliersService.toggleVehicleStatus(id, vehicleId);
    return new ApiResponse(result, 'Vehicle status updated successfully');
  }

  // ─── Drivers (Supplier-scoped) ────────────────────────

  @Get(':id/drivers')
  @Permissions('suppliers')
  async findDrivers(
    @Param('id') id: string,
    @Query() pagination: PaginationDto,
  ) {
    const page = pagination.page ?? 1;
    const limit = pagination.limit ?? 50;
    const result = await this.suppliersService.findDrivers(id, page, limit);
    return new ApiResponse(result);
  }

  @Post(':id/drivers')
  @Permissions('suppliers')
  async createDriver(
    @Param('id') id: string,
    @Body() dto: CreateSupplierDriverDto,
  ) {
    const result = await this.suppliersService.createDriver(id, dto);
    return new ApiResponse(result, 'Driver added successfully');
  }

  @Put(':id/drivers/:driverId')
  @Permissions('suppliers')
  async updateDriver(
    @Param('id') id: string,
    @Param('driverId') driverId: string,
    @Body() dto: UpdateSupplierDriverDto,
  ) {
    const result = await this.suppliersService.updateDriver(id, driverId, dto);
    return new ApiResponse(result, 'Driver updated successfully');
  }

  @Delete(':id/drivers/:driverId')
  @Permissions('suppliers')
  async deleteDriver(
    @Param('id') id: string,
    @Param('driverId') driverId: string,
  ) {
    await this.suppliersService.deleteDriver(id, driverId);
    return new ApiResponse(null, 'Driver removed successfully');
  }

  @Patch(':id/drivers/:driverId/status')
  @Permissions('suppliers')
  async toggleDriverStatus(
    @Param('id') id: string,
    @Param('driverId') driverId: string,
  ) {
    const result = await this.suppliersService.toggleDriverStatus(id, driverId);
    return new ApiResponse(result, 'Driver status updated successfully');
  }

  // ─── Price List (Bulk Upsert) ─────────────────────────

  @Get(':id/price-list')
  @Permissions('suppliers')
  async getPriceList(@Param('id') id: string) {
    const result = await this.suppliersService.getPriceList(id);
    return new ApiResponse(result);
  }

  @Post(':id/price-list')
  @Permissions('suppliers')
  async upsertPriceList(
    @Param('id') id: string,
    @Body() dto: BulkPriceListDto,
  ) {
    const result = await this.suppliersService.upsertPriceItems(id, dto);
    return new ApiResponse(result, 'Price list saved successfully');
  }

  @Delete(':id/price-list/:priceItemId')
  @Permissions('suppliers')
  async deletePriceItem(
    @Param('id') id: string,
    @Param('priceItemId') priceItemId: string,
  ) {
    await this.suppliersService.deletePriceItem(id, priceItemId);
    return new ApiResponse(null, 'Price item deleted successfully');
  }

  // ─── Vehicle Import/Export ────────────────────────────

  @Get(':id/vehicles/export')
  @Permissions('suppliers')
  async exportVehicles(
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const buffer = await this.suppliersService.exportVehiclesToExcel(id);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="supplier-vehicles-${id}.xlsx"`,
    });
    res.send(buffer);
  }

  @Get(':id/vehicles/template')
  @Permissions('suppliers')
  async getVehicleTemplate(
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const buffer = await this.suppliersService.generateVehicleImportTemplate(id);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="vehicle-import-template.xlsx"`,
    });
    res.send(buffer);
  }

  @Post(':id/vehicles/import')
  @Permissions('suppliers')
  @UseInterceptors(FileInterceptor('file'))
  async importVehicles(
    @Param('id') id: string,
    @UploadedFile() file: Express.Multer.File,
  ) {
    const result = await this.suppliersService.importVehiclesFromExcel(id, file.buffer);
    return new ApiResponse(result, 'Vehicles imported successfully');
  }

  // ─── Driver Import/Export ───────────────────────────────

  @Get(':id/drivers/export')
  @Permissions('suppliers')
  async exportDrivers(
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const buffer = await this.suppliersService.exportDriversToExcel(id);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="supplier-drivers-${id}.xlsx"`,
    });
    res.send(buffer);
  }

  @Get(':id/drivers/template')
  @Permissions('suppliers')
  async getDriverTemplate(
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const buffer = await this.suppliersService.generateDriverImportTemplate(id);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="driver-import-template.xlsx"`,
    });
    res.send(buffer);
  }

  @Post(':id/drivers/import')
  @Permissions('suppliers')
  @UseInterceptors(FileInterceptor('file'))
  async importDrivers(
    @Param('id') id: string,
    @UploadedFile() file: Express.Multer.File,
  ) {
    const result = await this.suppliersService.importDriversFromExcel(id, file.buffer);
    return new ApiResponse(result, 'Drivers imported successfully');
  }

  // ─── Price List Import/Export ───────────────────────────

  @Get(':id/price-list/export')
  @Permissions('suppliers')
  async exportPriceList(
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const buffer = await this.suppliersService.exportPriceListToExcel(id);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="supplier-price-list-${id}.xlsx"`,
    });
    res.send(buffer);
  }

  @Get(':id/price-list/template')
  @Permissions('suppliers')
  async getPriceListTemplate(
    @Param('id') id: string,
    @Res() res: Response,
  ) {
    const buffer = await this.suppliersService.generatePriceListTemplate(id);
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="price-list-import-template.xlsx"`,
    });
    res.send(buffer);
  }

  @Post(':id/price-list/import')
  @Permissions('suppliers')
  @UseInterceptors(FileInterceptor('file'))
  async importPriceList(
    @Param('id') id: string,
    @UploadedFile() file: Express.Multer.File,
  ) {
    const result = await this.suppliersService.importPriceListFromExcel(id, file.buffer);
    return new ApiResponse(result, 'Price list imported successfully');
  }

  // ─── Account Management ───────────────────────────────

  @Post(':id/account')
  @Roles('ADMIN')
  @Permissions('suppliers.table.createAccount')
  async createAccount(
    @Param('id') id: string,
    @Body() dto: { password: string },
  ) {
    const result = await this.suppliersService.createUserAccount(id, dto);
    return new ApiResponse(result, 'Supplier account created successfully');
  }

  @Patch(':id/account/password')
  @Roles('ADMIN')
  @Permissions('suppliers.table.resetPassword')
  async resetPassword(
    @Param('id') id: string,
    @Body() dto: { password: string },
  ) {
    const result = await this.suppliersService.resetPassword(id, dto.password);
    return new ApiResponse(result, 'Password reset successfully');
  }

  // ─── National ID Upload ─────────────────────────────────

  @Post(':id/national-id')
  @Permissions('suppliers.table.editButton')
  @UseInterceptors(FileInterceptor('file'))
  async uploadNationalId(
    @Param('id', ParseUUIDPipe) id: string,
    @UploadedFile() file: any,
  ) {
    if (!file) {
      return new ApiResponse(null, 'No file uploaded');
    }
    const fs = await import('fs/promises');
    const path = await import('path');
    const uploadDir = path.join(process.cwd(), 'uploads', 'national-ids');
    await fs.mkdir(uploadDir, { recursive: true });
    const ext = path.extname(file.originalname) || '.jpg';
    const filename = `${id}${ext}`;
    await fs.writeFile(path.join(uploadDir, filename), file.buffer);
    const imageUrl = `/uploads/national-ids/${filename}`;
    await this.suppliersService.update(id, { nationalIdImage: imageUrl } as any);
    return new ApiResponse({ url: imageUrl }, 'National ID uploaded');
  }

  // ── Supplier Car Types ──

  @Get(':id/car-types')
  @Permissions('suppliers')
  async getCarTypes(@Param('id') id: string) {
    return new ApiResponse(await this.suppliersService.getCarTypes(id));
  }

  @Put(':id/car-types')
  @Permissions('suppliers.table.editButton')
  async setCarTypes(
    @Param('id') id: string,
    @Body() body: { vehicleTypeIds: string[] },
  ) {
    return new ApiResponse(
      await this.suppliersService.setCarTypes(id, body.vehicleTypeIds),
    );
  }
}
