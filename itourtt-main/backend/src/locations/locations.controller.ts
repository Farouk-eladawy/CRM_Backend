import {
  Controller,
  Get,
  Post,
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
  BadRequestException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import type { Response } from 'express';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { LocationsService } from './locations.service.js';
import { GeocodingService } from '../common/geocoding.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { CreateCountryDto } from './dto/create-country.dto.js';
import { CreateAirportDto } from './dto/create-airport.dto.js';
import { CreateCityDto } from './dto/create-city.dto.js';
import { CreateZoneDto } from './dto/create-zone.dto.js';
import { CreateHotelDto } from './dto/create-hotel.dto.js';
import { UpdateCountryDto } from './dto/update-country.dto.js';
import { UpdateAirportDto } from './dto/update-airport.dto.js';
import { UpdateCityDto } from './dto/update-city.dto.js';
import { UpdateZoneDto } from './dto/update-zone.dto.js';
import { UpdateHotelDto } from './dto/update-hotel.dto.js';

@Controller('locations')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class LocationsController {
  constructor(
    private readonly locationsService: LocationsService,
    private readonly geocodingService: GeocodingService,
  ) {}

  // ─── Export / Import ──────────────────────────────────────

  @Get('export/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.export')
  async exportExcel(@Res() res: Response) {
    const buffer = await this.locationsService.exportToExcel();
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="locations_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('import/template')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.downloadTemplate')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.locationsService.generateImportTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="locations_import_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.import')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.locationsService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} locations with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} locations`;
    return new ApiResponse(result, message);
  }

  // ─── Google Places Search ────────────────────────────────

  @Get('places-search')
  @Permissions('locations')
  async placesSearch(
    @Query('q') q: string,
    @Query('type') type?: string,
  ) {
    if (!q || q.trim().length < 2) {
      throw new BadRequestException('Query must be at least 2 characters');
    }
    const results = await this.geocodingService.searchPlaces(q.trim(), type);
    return new ApiResponse(results);
  }

  // ─── Batch Geocode ─────────────────────────────────────

  @Post('batch-geocode')
  @Roles('ADMIN')
  @Permissions('locations')
  async batchGeocode() {
    const result = await this.locationsService.batchGeocode();
    return new ApiResponse(result);
  }

  // ─── Update Location Coordinates ────────────────────────

  @Patch(':level/:id/coordinates')
  @Roles('ADMIN')
  @Permissions('locations')
  async updateCoordinates(
    @Param('level') level: string,
    @Param('id') id: string,
    @Body() body: { latitude: number; longitude: number; placeId?: string },
  ) {
    if (body.latitude == null || body.longitude == null) {
      throw new BadRequestException('latitude and longitude are required');
    }
    const result = await this.locationsService.updateLocationCoordinates(
      level,
      id,
      body.latitude,
      body.longitude,
      body.placeId,
    );
    return new ApiResponse(result);
  }

  // ─── Search ──────────────────────────────────────────────

  @Get('search')
  @Permissions('locations')
  searchLocations(
    @Query('q') q?: string,
    @Query('types') types?: string,
  ) {
    const typeArray = types ? types.split(',').map(t => t.trim().toUpperCase()) : undefined;
    return this.locationsService.searchLocations(q, typeArray);
  }

  // ─── Full Location Tree ───────────────────────────────────

  @Get('tree')
  @Permissions('locations')
  getTree() {
    return this.locationsService.getTree();
  }

  // ─── Countries ────────────────────────────────────────────

  @Get('countries')
  @Permissions('locations.countries')
  findAllCountries(@Query() pagination: PaginationDto) {
    const page = pagination.page ?? 1;
    const limit = pagination.limit ?? 20;
    return this.locationsService.findAllCountries(page, limit);
  }

  @Post('countries')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.countries.addButton')
  createCountry(@Body() dto: CreateCountryDto) {
    return this.locationsService.createCountry(dto);
  }

  // ─── Airports ─────────────────────────────────────────────

  @Get('airports')
  @Permissions('locations.airports')
  findAirportsByCountry(@Query('countryId') countryId?: string) {
    return this.locationsService.findAirportsByCountry(countryId);
  }

  @Post('airports')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.airports.addButton')
  createAirport(@Body() dto: CreateAirportDto) {
    return this.locationsService.createAirport(dto);
  }

  // ─── Cities ───────────────────────────────────────────────

  @Get('cities')
  @Permissions('locations.cities')
  findCitiesByAirport(@Query('airportId', ParseUUIDPipe) airportId: string) {
    return this.locationsService.findCitiesByAirport(airportId);
  }

  @Post('cities')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.cities.addButton')
  createCity(@Body() dto: CreateCityDto) {
    return this.locationsService.createCity(dto);
  }

  // ─── Zones ────────────────────────────────────────────────

  @Get('zones')
  @Permissions('locations.zones')
  findZones(@Query('cityId') cityId?: string) {
    return this.locationsService.findZones(cityId);
  }

  @Post('zones')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.zones.addButton')
  createZone(@Body() dto: CreateZoneDto) {
    return this.locationsService.createZone(dto);
  }

  // ─── Hotels ───────────────────────────────────────────────

  @Get('zones/:id/hotels')
  @Permissions('locations.hotels')
  findHotelsByZone(@Param('id') zoneId: string) {
    return this.locationsService.findHotelsByZone(zoneId);
  }

  @Post('hotels')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.hotels.addButton')
  createHotel(@Body() dto: CreateHotelDto) {
    return this.locationsService.createHotel(dto);
  }

  // ─── Update ─────────────────────────────────────────────────

  @Patch('countries/:id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.countries.addButton')
  updateCountry(@Param('id', ParseUUIDPipe) id: string, @Body() dto: UpdateCountryDto) {
    return this.locationsService.updateCountry(id, dto);
  }

  @Patch('airports/:id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.airports.addButton')
  updateAirport(@Param('id', ParseUUIDPipe) id: string, @Body() dto: UpdateAirportDto) {
    return this.locationsService.updateAirport(id, dto);
  }

  @Patch('cities/:id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.cities.addButton')
  updateCity(@Param('id', ParseUUIDPipe) id: string, @Body() dto: UpdateCityDto) {
    return this.locationsService.updateCity(id, dto);
  }

  @Patch('zones/:id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.zones.addButton')
  updateZone(@Param('id', ParseUUIDPipe) id: string, @Body() dto: UpdateZoneDto) {
    return this.locationsService.updateZone(id, dto);
  }

  @Patch('hotels/:id')
  @Roles('ADMIN', 'DISPATCHER')
  @Permissions('locations.hotels.addButton')
  updateHotel(@Param('id', ParseUUIDPipe) id: string, @Body() dto: UpdateHotelDto) {
    return this.locationsService.updateHotel(id, dto);
  }

  // ─── Delete ─────────────────────────────────────────────────

  @Delete('countries/:id')
  @Roles('ADMIN')
  @Permissions('locations.countries.addButton')
  deleteCountry(@Param('id') id: string) {
    return this.locationsService.deleteCountry(id);
  }

  @Delete('airports/:id')
  @Roles('ADMIN')
  @Permissions('locations.airports.deleteButton')
  deleteAirport(@Param('id') id: string) {
    return this.locationsService.deleteAirport(id);
  }

  @Delete('cities/:id')
  @Roles('ADMIN')
  @Permissions('locations.cities.deleteButton')
  deleteCity(@Param('id') id: string) {
    return this.locationsService.deleteCity(id);
  }

  @Delete('zones/:id')
  @Roles('ADMIN')
  @Permissions('locations.zones.deleteButton')
  deleteZone(@Param('id') id: string) {
    return this.locationsService.deleteZone(id);
  }

  @Delete('hotels/:id')
  @Roles('ADMIN')
  @Permissions('locations.hotels.deleteButton')
  deleteHotel(@Param('id') id: string) {
    return this.locationsService.deleteHotel(id);
  }
}
