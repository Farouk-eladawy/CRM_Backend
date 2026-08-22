import { Injectable, NotFoundException, BadRequestException, Logger } from '@nestjs/common';
import ExcelJS from 'exceljs';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { GeocodingService } from '../common/geocoding.service.js';
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

@Injectable()
export class LocationsService {
  private readonly logger = new Logger(LocationsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly geocoding: GeocodingService,
  ) {}

  // ─── Search ──────────────────────────────────────────────

  async searchLocations(query?: string, types?: string[]) {
    // Default to all types if not specified
    const searchTypes = types?.length ? types : ['AIRPORT', 'ZONE', 'HOTEL'];
    const results: Array<{ id: string; type: string; name: string; code?: string; path: string }> = [];
    const q = query?.toLowerCase()?.trim();

    if (searchTypes.includes('AIRPORT')) {
      const airports = await this.prisma.airport.findMany({
        where: {
          deletedAt: null,
          ...(q ? { OR: [
            { name: { contains: q, mode: 'insensitive' } },
            { code: { contains: q, mode: 'insensitive' } },
          ] } : {}),
        },
        include: { country: true },
        orderBy: { name: 'asc' },
        take: 50,
      });
      for (const a of airports) {
        results.push({
          id: a.id,
          type: 'AIRPORT',
          name: a.name,
          code: a.code,
          path: `${a.country.name} > ${a.name}`,
        });
      }
    }

    if (searchTypes.includes('ZONE')) {
      const zones = await this.prisma.zone.findMany({
        where: {
          deletedAt: null,
          ...(q ? { name: { contains: q, mode: 'insensitive' } } : {}),
        },
        include: { city: { include: { airport: { include: { country: true } } } } },
        orderBy: { name: 'asc' },
        take: 50,
      });
      for (const z of zones) {
        results.push({
          id: z.id,
          type: 'ZONE',
          name: z.name,
          path: `${z.city.airport.country.name} > ${z.city.airport.name} > ${z.city.name} > ${z.name}`,
        });
      }
    }

    if (searchTypes.includes('HOTEL')) {
      const hotels = await this.prisma.hotel.findMany({
        where: {
          deletedAt: null,
          ...(q ? { name: { contains: q, mode: 'insensitive' } } : {}),
        },
        include: { zone: { include: { city: { include: { airport: { include: { country: true } } } } } } },
        orderBy: { name: 'asc' },
        take: 50,
      });
      for (const h of hotels) {
        results.push({
          id: h.id,
          type: 'HOTEL',
          name: h.name,
          path: `${h.zone.city.airport.country.name} > ${h.zone.city.airport.name} > ${h.zone.city.name} > ${h.zone.name} > ${h.name}`,
        });
      }
    }

    return results;
  }

  // ─── Full Location Tree ───────────────────────────────────

  async getTree() {
    const countries = await this.prisma.country.findMany({
      where: { deletedAt: null },
      orderBy: { name: 'asc' },
      include: {
        airports: {
          where: { deletedAt: null },
          orderBy: { name: 'asc' },
          include: {
            cities: {
              where: { deletedAt: null },
              orderBy: { name: 'asc' },
              include: {
                zones: {
                  where: { deletedAt: null },
                  orderBy: { name: 'asc' },
                  include: {
                    hotels: {
                      where: { deletedAt: null },
                      orderBy: { name: 'asc' },
                    },
                  },
                },
              },
            },
          },
        },
      },
    });

    return countries;
  }

  // ─── Countries ────────────────────────────────────────────

  async findAllCountries(page: number, limit: number) {
    const skip = (page - 1) * limit;

    const [data, total] = await Promise.all([
      this.prisma.country.findMany({
        where: { deletedAt: null },
        orderBy: { name: 'asc' },
        skip,
        take: limit,
      }),
      this.prisma.country.count({
        where: { deletedAt: null },
      }),
    ]);

    return {
      data,
      meta: {
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  async createCountry(dto: CreateCountryDto) {
    return this.prisma.country.create({
      data: {
        name: dto.name,
        code: dto.code.toUpperCase(),
        ...(dto.latitude != null && { latitude: dto.latitude }),
        ...(dto.longitude != null && { longitude: dto.longitude }),
        ...(dto.placeId && { placeId: dto.placeId }),
      },
    });
  }

  // ─── Airports ─────────────────────────────────────────────

  async findAirportsByCountry(countryId?: string) {
    if (countryId) {
      const country = await this.prisma.country.findUnique({
        where: { id: countryId, deletedAt: null },
      });
      if (!country) {
        throw new NotFoundException(`Country with id ${countryId} not found`);
      }
    }

    return this.prisma.airport.findMany({
      where: { ...(countryId ? { countryId } : {}), deletedAt: null, isActive: true },
      orderBy: { name: 'asc' },
      include: { country: true },
    });
  }

  async createAirport(dto: CreateAirportDto) {
    const country = await this.prisma.country.findUnique({
      where: { id: dto.countryId, deletedAt: null },
    });
    if (!country) {
      throw new NotFoundException(`Country with id ${dto.countryId} not found`);
    }

    return this.prisma.airport.create({
      data: {
        name: dto.name,
        code: dto.code.toUpperCase(),
        countryId: dto.countryId,
        ...(dto.latitude != null && { latitude: dto.latitude }),
        ...(dto.longitude != null && { longitude: dto.longitude }),
        ...(dto.placeId && { placeId: dto.placeId }),
      },
      include: { country: true },
    });
  }

  // ─── Cities ───────────────────────────────────────────────

  async findCitiesByAirport(airportId: string) {
    const airport = await this.prisma.airport.findUnique({
      where: { id: airportId, deletedAt: null },
    });
    if (!airport) {
      throw new NotFoundException(`Airport with id ${airportId} not found`);
    }

    return this.prisma.city.findMany({
      where: { airportId, deletedAt: null },
      orderBy: { name: 'asc' },
      include: { airport: true },
    });
  }

  async createCity(dto: CreateCityDto) {
    const airport = await this.prisma.airport.findUnique({
      where: { id: dto.airportId, deletedAt: null },
    });
    if (!airport) {
      throw new NotFoundException(`Airport with id ${dto.airportId} not found`);
    }

    return this.prisma.city.create({
      data: {
        name: dto.name,
        airportId: dto.airportId,
        ...(dto.latitude != null && { latitude: dto.latitude }),
        ...(dto.longitude != null && { longitude: dto.longitude }),
        ...(dto.placeId && { placeId: dto.placeId }),
      },
      include: { airport: true },
    });
  }

  // ─── Zones ────────────────────────────────────────────────

  async findZones(cityId?: string) {
    if (cityId) {
      const city = await this.prisma.city.findUnique({
        where: { id: cityId, deletedAt: null },
      });
      if (!city) {
        throw new NotFoundException(`City with id ${cityId} not found`);
      }
    }

    return this.prisma.zone.findMany({
      where: { deletedAt: null, ...(cityId ? { cityId } : {}) },
      orderBy: { name: 'asc' },
      include: { city: true },
    });
  }

  async createZone(dto: CreateZoneDto) {
    const city = await this.prisma.city.findUnique({
      where: { id: dto.cityId, deletedAt: null },
    });
    if (!city) {
      throw new NotFoundException(`City with id ${dto.cityId} not found`);
    }

    return this.prisma.zone.create({
      data: {
        name: dto.name,
        cityId: dto.cityId,
        ...(dto.latitude != null && { latitude: dto.latitude }),
        ...(dto.longitude != null && { longitude: dto.longitude }),
        ...(dto.placeId && { placeId: dto.placeId }),
      },
      include: { city: true },
    });
  }

  // ─── Hotels ───────────────────────────────────────────────

  async findHotelsByZone(zoneId: string) {
    const zone = await this.prisma.zone.findUnique({
      where: { id: zoneId, deletedAt: null },
    });
    if (!zone) {
      throw new NotFoundException(`Zone with id ${zoneId} not found`);
    }

    return this.prisma.hotel.findMany({
      where: { zoneId, deletedAt: null },
      orderBy: { name: 'asc' },
      include: { zone: true },
    });
  }

  async createHotel(dto: CreateHotelDto) {
    const zone = await this.prisma.zone.findUnique({
      where: { id: dto.zoneId, deletedAt: null },
    });
    if (!zone) {
      throw new NotFoundException(`Zone with id ${dto.zoneId} not found`);
    }

    return this.prisma.hotel.create({
      data: {
        name: dto.name,
        zoneId: dto.zoneId,
        address: dto.address,
        stars: dto.stars,
        ...(dto.latitude != null && { latitude: dto.latitude }),
        ...(dto.longitude != null && { longitude: dto.longitude }),
        ...(dto.placeId && { placeId: dto.placeId }),
      },
      include: { zone: true },
    });
  }

  // ─── Update Methods ──────────────────────────────────────

  async updateCountry(id: string, dto: UpdateCountryDto) {
    const country = await this.prisma.country.findUnique({ where: { id, deletedAt: null } });
    if (!country) throw new NotFoundException(`Country with id ${id} not found`);

    return this.prisma.country.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.code !== undefined && { code: dto.code.toUpperCase() }),
        ...(dto.latitude !== undefined && { latitude: dto.latitude }),
        ...(dto.longitude !== undefined && { longitude: dto.longitude }),
        ...(dto.placeId !== undefined && { placeId: dto.placeId }),
      },
    });
  }

  async updateAirport(id: string, dto: UpdateAirportDto) {
    const airport = await this.prisma.airport.findUnique({ where: { id, deletedAt: null } });
    if (!airport) throw new NotFoundException(`Airport with id ${id} not found`);

    if (dto.countryId) {
      const country = await this.prisma.country.findUnique({ where: { id: dto.countryId, deletedAt: null } });
      if (!country) throw new NotFoundException(`Country with id ${dto.countryId} not found`);
    }

    return this.prisma.airport.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.code !== undefined && { code: dto.code.toUpperCase() }),
        ...(dto.countryId !== undefined && { countryId: dto.countryId }),
        ...(dto.latitude !== undefined && { latitude: dto.latitude }),
        ...(dto.longitude !== undefined && { longitude: dto.longitude }),
        ...(dto.placeId !== undefined && { placeId: dto.placeId }),
      },
      include: { country: true },
    });
  }

  async updateCity(id: string, dto: UpdateCityDto) {
    const city = await this.prisma.city.findUnique({ where: { id, deletedAt: null } });
    if (!city) throw new NotFoundException(`City with id ${id} not found`);

    if (dto.airportId) {
      const airport = await this.prisma.airport.findUnique({ where: { id: dto.airportId, deletedAt: null } });
      if (!airport) throw new NotFoundException(`Airport with id ${dto.airportId} not found`);
    }

    return this.prisma.city.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.airportId !== undefined && { airportId: dto.airportId }),
        ...(dto.latitude !== undefined && { latitude: dto.latitude }),
        ...(dto.longitude !== undefined && { longitude: dto.longitude }),
        ...(dto.placeId !== undefined && { placeId: dto.placeId }),
      },
      include: { airport: true },
    });
  }

  async updateZone(id: string, dto: UpdateZoneDto) {
    const zone = await this.prisma.zone.findUnique({ where: { id, deletedAt: null } });
    if (!zone) throw new NotFoundException(`Zone with id ${id} not found`);

    if (dto.cityId) {
      const city = await this.prisma.city.findUnique({ where: { id: dto.cityId, deletedAt: null } });
      if (!city) throw new NotFoundException(`City with id ${dto.cityId} not found`);
    }

    return this.prisma.zone.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.cityId !== undefined && { cityId: dto.cityId }),
        ...(dto.latitude !== undefined && { latitude: dto.latitude }),
        ...(dto.longitude !== undefined && { longitude: dto.longitude }),
        ...(dto.placeId !== undefined && { placeId: dto.placeId }),
      },
      include: { city: true },
    });
  }

  async updateHotel(id: string, dto: UpdateHotelDto) {
    const hotel = await this.prisma.hotel.findUnique({ where: { id, deletedAt: null } });
    if (!hotel) throw new NotFoundException(`Hotel with id ${id} not found`);

    if (dto.zoneId) {
      const zone = await this.prisma.zone.findUnique({ where: { id: dto.zoneId, deletedAt: null } });
      if (!zone) throw new NotFoundException(`Zone with id ${dto.zoneId} not found`);
    }

    return this.prisma.hotel.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.zoneId !== undefined && { zoneId: dto.zoneId }),
        ...(dto.address !== undefined && { address: dto.address }),
        ...(dto.stars !== undefined && { stars: dto.stars }),
        ...(dto.latitude !== undefined && { latitude: dto.latitude }),
        ...(dto.longitude !== undefined && { longitude: dto.longitude }),
        ...(dto.placeId !== undefined && { placeId: dto.placeId }),
      },
      include: { zone: true },
    });
  }

  // ─── Soft-Delete Methods ──────────────────────────────────

  async deleteCountry(id: string) {
    const country = await this.prisma.country.findUnique({
      where: { id, deletedAt: null },
      include: { airports: { where: { deletedAt: null }, select: { id: true }, take: 1 } },
    });
    if (!country) throw new NotFoundException(`Country with id ${id} not found`);
    if (country.airports.length > 0) {
      throw new BadRequestException('Cannot delete country that still has airports. Delete children first.');
    }
    return this.prisma.country.update({ where: { id }, data: { deletedAt: new Date() } });
  }

  async deleteAirport(id: string) {
    const airport = await this.prisma.airport.findUnique({
      where: { id, deletedAt: null },
      include: { cities: { where: { deletedAt: null }, select: { id: true }, take: 1 } },
    });
    if (!airport) throw new NotFoundException(`Airport with id ${id} not found`);
    if (airport.cities.length > 0) {
      throw new BadRequestException('Cannot delete airport that still has cities. Delete children first.');
    }
    return this.prisma.airport.update({ where: { id }, data: { deletedAt: new Date() } });
  }

  async deleteCity(id: string) {
    const city = await this.prisma.city.findUnique({
      where: { id, deletedAt: null },
      include: { zones: { where: { deletedAt: null }, select: { id: true }, take: 1 } },
    });
    if (!city) throw new NotFoundException(`City with id ${id} not found`);
    if (city.zones.length > 0) {
      throw new BadRequestException('Cannot delete city that still has zones. Delete children first.');
    }
    return this.prisma.city.update({ where: { id }, data: { deletedAt: new Date() } });
  }

  async deleteZone(id: string) {
    const zone = await this.prisma.zone.findUnique({
      where: { id, deletedAt: null },
      include: { hotels: { where: { deletedAt: null }, select: { id: true }, take: 1 } },
    });
    if (!zone) throw new NotFoundException(`Zone with id ${id} not found`);
    if (zone.hotels.length > 0) {
      throw new BadRequestException('Cannot delete zone that still has hotels. Delete children first.');
    }
    return this.prisma.zone.update({ where: { id }, data: { deletedAt: new Date() } });
  }

  async deleteHotel(id: string) {
    const hotel = await this.prisma.hotel.findUnique({
      where: { id, deletedAt: null },
    });
    if (!hotel) throw new NotFoundException(`Hotel with id ${id} not found`);
    return this.prisma.hotel.update({ where: { id }, data: { deletedAt: new Date() } });
  }

  // ──────────────────────────────────────────────
  // EXPORT – full location tree to Excel
  // ──────────────────────────────────────────────

  async exportToExcel(): Promise<Buffer> {
    const tree = await this.getTree();

    const wb = XLSX.utils.book_new();

    // Countries sheet
    const countryRows = tree.map((c: any) => ({ Name: c.name, Code: c.code }));
    const ws1 = XLSX.utils.json_to_sheet(countryRows.length > 0 ? countryRows : [{}]);
    ws1['!cols'] = [{ wch: 25 }, { wch: 10 }];
    XLSX.utils.book_append_sheet(wb, ws1, 'Countries');

    // Airports sheet
    const airportRows: any[] = [];
    for (const c of tree) {
      for (const a of (c as any).airports || []) {
        airportRows.push({ Name: a.name, Code: a.code, 'Country Name': c.name });
      }
    }
    const ws2 = XLSX.utils.json_to_sheet(airportRows.length > 0 ? airportRows : [{}]);
    ws2['!cols'] = [{ wch: 30 }, { wch: 10 }, { wch: 25 }];
    XLSX.utils.book_append_sheet(wb, ws2, 'Airports');

    // Cities sheet
    const cityRows: any[] = [];
    for (const c of tree) {
      for (const a of (c as any).airports || []) {
        for (const ci of a.cities || []) {
          cityRows.push({ Name: ci.name, 'Airport Name': a.name });
        }
      }
    }
    const ws3 = XLSX.utils.json_to_sheet(cityRows.length > 0 ? cityRows : [{}]);
    ws3['!cols'] = [{ wch: 25 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, ws3, 'Cities');

    // Zones sheet
    const zoneRows: any[] = [];
    for (const c of tree) {
      for (const a of (c as any).airports || []) {
        for (const ci of a.cities || []) {
          for (const z of ci.zones || []) {
            zoneRows.push({ Name: z.name, 'City Name': ci.name });
          }
        }
      }
    }
    const ws4 = XLSX.utils.json_to_sheet(zoneRows.length > 0 ? zoneRows : [{}]);
    ws4['!cols'] = [{ wch: 25 }, { wch: 25 }];
    XLSX.utils.book_append_sheet(wb, ws4, 'Zones');

    // Hotels sheet
    const hotelRows: any[] = [];
    for (const c of tree) {
      for (const a of (c as any).airports || []) {
        for (const ci of a.cities || []) {
          for (const z of ci.zones || []) {
            for (const h of z.hotels || []) {
              hotelRows.push({ Name: h.name, 'Zone Name': z.name, Address: h.address || '', Stars: h.stars ?? '' });
            }
          }
        }
      }
    }
    const ws5 = XLSX.utils.json_to_sheet(hotelRows.length > 0 ? hotelRows : [{}]);
    ws5['!cols'] = [{ wch: 30 }, { wch: 25 }, { wch: 30 }, { wch: 8 }];
    XLSX.utils.book_append_sheet(wb, ws5, 'Hotels');

    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ──────────────────────────────────────────────
  // IMPORT TEMPLATE – generate location template
  // ──────────────────────────────────────────────

  async generateImportTemplate(): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    const headerStyle: Partial<ExcelJS.Style> = {
      font: { bold: true, color: { argb: 'FFFFFFFF' } },
      fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF4472C4' } },
      alignment: { vertical: 'middle', horizontal: 'center' },
    };

    const sampleStyle: Partial<ExcelJS.Font> = { italic: true, color: { argb: 'FF999999' } };

    // Instructions
    const instr = workbook.addWorksheet('Instructions');
    instr.columns = [{ width: 80 }];
    instr.addRow(['Location Tree Bulk Import Template']);
    instr.addRow(['']);
    instr.addRow(['Instructions:']);
    instr.addRow(['1. Each sheet represents one level of the location hierarchy']);
    instr.addRow(['2. Process order: Countries → Airports → Cities → Zones → Hotels']);
    instr.addRow(['3. Parent references must match existing names exactly (case-insensitive)']);
    instr.addRow(['4. Countries and Airports require a Code field (e.g., "EG", "CAI")']);
    instr.addRow(['5. Hotels have optional Address and Stars fields']);
    instr.addRow(['6. Do not modify column headers']);
    instr.addRow(['7. You can leave sheets empty if you only need to import certain levels']);
    instr.addRow(['']);
    instr.addRow(['Notes:']);
    instr.addRow(['- Duplicate names at the same level will be skipped']);
    instr.addRow(['- Parent must exist (either in DB or imported in a prior sheet)']);
    instr.getRow(1).font = { bold: true, size: 14 };
    instr.getRow(3).font = { bold: true };
    instr.getRow(12).font = { bold: true };

    // Countries
    const countriesSheet = workbook.addWorksheet('Countries');
    countriesSheet.columns = [
      { header: 'Name', key: 'name', width: 25 },
      { header: 'Code', key: 'code', width: 10 },
    ];
    Object.assign(countriesSheet.getRow(1), headerStyle);
    countriesSheet.getRow(1).font = headerStyle.font!;
    countriesSheet.getRow(1).fill = headerStyle.fill as ExcelJS.Fill;
    countriesSheet.addRow({ name: 'Egypt', code: 'EG' });
    countriesSheet.getRow(2).font = sampleStyle;

    // Airports
    const airportsSheet = workbook.addWorksheet('Airports');
    airportsSheet.columns = [
      { header: 'Name', key: 'name', width: 30 },
      { header: 'Code', key: 'code', width: 10 },
      { header: 'Country Name', key: 'countryName', width: 25 },
    ];
    airportsSheet.getRow(1).font = headerStyle.font!;
    airportsSheet.getRow(1).fill = headerStyle.fill as ExcelJS.Fill;
    airportsSheet.addRow({ name: 'Cairo International Airport', code: 'CAI', countryName: 'Egypt' });
    airportsSheet.getRow(2).font = sampleStyle;

    // Cities
    const citiesSheet = workbook.addWorksheet('Cities');
    citiesSheet.columns = [
      { header: 'Name', key: 'name', width: 25 },
      { header: 'Airport Name', key: 'airportName', width: 30 },
    ];
    citiesSheet.getRow(1).font = headerStyle.font!;
    citiesSheet.getRow(1).fill = headerStyle.fill as ExcelJS.Fill;
    citiesSheet.addRow({ name: 'Cairo', airportName: 'Cairo International Airport' });
    citiesSheet.getRow(2).font = sampleStyle;

    // Zones
    const zonesSheet = workbook.addWorksheet('Zones');
    zonesSheet.columns = [
      { header: 'Name', key: 'name', width: 25 },
      { header: 'City Name', key: 'cityName', width: 25 },
    ];
    zonesSheet.getRow(1).font = headerStyle.font!;
    zonesSheet.getRow(1).fill = headerStyle.fill as ExcelJS.Fill;
    zonesSheet.addRow({ name: 'Downtown', cityName: 'Cairo' });
    zonesSheet.getRow(2).font = sampleStyle;

    // Hotels
    const hotelsSheet = workbook.addWorksheet('Hotels');
    hotelsSheet.columns = [
      { header: 'Name', key: 'name', width: 30 },
      { header: 'Zone Name', key: 'zoneName', width: 25 },
      { header: 'Address', key: 'address', width: 30 },
      { header: 'Stars', key: 'stars', width: 8 },
    ];
    hotelsSheet.getRow(1).font = headerStyle.font!;
    hotelsSheet.getRow(1).fill = headerStyle.fill as ExcelJS.Fill;
    hotelsSheet.addRow({ name: 'Nile Hilton', zoneName: 'Downtown', address: 'Corniche El Nil', stars: 5 });
    hotelsSheet.getRow(2).font = sampleStyle;

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  // ──────────────────────────────────────────────
  // BULK IMPORT – parse location tree from Excel
  // ──────────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    let imported = 0;
    const errors: string[] = [];

    // Build lookup maps from existing data
    const existingCountries = await this.prisma.country.findMany({ where: { deletedAt: null } });
    const countryMap = new Map(existingCountries.map((c) => [c.name.toLowerCase(), c.id]));

    const existingAirports = await this.prisma.airport.findMany({ where: { deletedAt: null } });
    const airportMap = new Map(existingAirports.map((a) => [a.name.toLowerCase(), a.id]));

    const existingCities = await this.prisma.city.findMany({ where: { deletedAt: null } });
    const cityMap = new Map(existingCities.map((c) => [c.name.toLowerCase(), c.id]));

    const existingZones = await this.prisma.zone.findMany({ where: { deletedAt: null } });
    const zoneMap = new Map(existingZones.map((z) => [z.name.toLowerCase(), z.id]));

    // 1. Countries
    const countriesSheet = workbook.getWorksheet('Countries');
    if (countriesSheet) {
      countriesSheet.eachRow((row, rowNumber) => {});
      const countryItems: { name: string; code: string }[] = [];
      countriesSheet.eachRow((row, rowNumber) => {
        if (rowNumber === 1) return;
        const name = String(row.getCell(1).value || '').trim();
        const code = String(row.getCell(2).value || '').trim().toUpperCase();
        if (!name) return;
        if (name === 'Egypt' && code === 'EG') return; // Skip sample
        if (countryMap.has(name.toLowerCase())) {
          errors.push(`Countries row ${rowNumber}: "${name}" already exists — skipped`);
          return;
        }
        if (!code) {
          errors.push(`Countries row ${rowNumber}: Code is required for "${name}"`);
          return;
        }
        countryItems.push({ name, code });
      });

      for (const item of countryItems) {
        try {
          const created = await this.prisma.country.create({ data: item });
          countryMap.set(created.name.toLowerCase(), created.id);
          imported++;
        } catch (err: any) {
          errors.push(`Failed country "${item.name}": ${err.message}`);
        }
      }
    }

    // 2. Airports
    const airportsSheet = workbook.getWorksheet('Airports');
    if (airportsSheet) {
      const airportItems: { name: string; code: string; countryId: string }[] = [];
      airportsSheet.eachRow((row, rowNumber) => {
        if (rowNumber === 1) return;
        const name = String(row.getCell(1).value || '').trim();
        const code = String(row.getCell(2).value || '').trim().toUpperCase();
        const countryName = String(row.getCell(3).value || '').trim();
        if (!name) return;
        if (name === 'Cairo International Airport' && code === 'CAI') return;
        if (airportMap.has(name.toLowerCase())) {
          errors.push(`Airports row ${rowNumber}: "${name}" already exists — skipped`);
          return;
        }
        if (!code) {
          errors.push(`Airports row ${rowNumber}: Code is required for "${name}"`);
          return;
        }
        const countryId = countryMap.get(countryName.toLowerCase());
        if (!countryId) {
          errors.push(`Airports row ${rowNumber}: Country "${countryName}" not found`);
          return;
        }
        airportItems.push({ name, code, countryId });
      });

      for (const item of airportItems) {
        try {
          const created = await this.prisma.airport.create({ data: item });
          airportMap.set(created.name.toLowerCase(), created.id);
          imported++;
        } catch (err: any) {
          errors.push(`Failed airport "${item.name}": ${err.message}`);
        }
      }
    }

    // 3. Cities
    const citiesSheet = workbook.getWorksheet('Cities');
    if (citiesSheet) {
      const cityItems: { name: string; airportId: string }[] = [];
      citiesSheet.eachRow((row, rowNumber) => {
        if (rowNumber === 1) return;
        const name = String(row.getCell(1).value || '').trim();
        const airportName = String(row.getCell(2).value || '').trim();
        if (!name) return;
        if (name === 'Cairo' && airportName === 'Cairo International Airport') return;
        if (cityMap.has(name.toLowerCase())) {
          errors.push(`Cities row ${rowNumber}: "${name}" already exists — skipped`);
          return;
        }
        const airportId = airportMap.get(airportName.toLowerCase());
        if (!airportId) {
          errors.push(`Cities row ${rowNumber}: Airport "${airportName}" not found`);
          return;
        }
        cityItems.push({ name, airportId });
      });

      for (const item of cityItems) {
        try {
          const created = await this.prisma.city.create({ data: item });
          cityMap.set(created.name.toLowerCase(), created.id);
          imported++;
        } catch (err: any) {
          errors.push(`Failed city "${item.name}": ${err.message}`);
        }
      }
    }

    // 4. Zones
    const zonesSheet = workbook.getWorksheet('Zones');
    if (zonesSheet) {
      const zoneItems: { name: string; cityId: string }[] = [];
      zonesSheet.eachRow((row, rowNumber) => {
        if (rowNumber === 1) return;
        const name = String(row.getCell(1).value || '').trim();
        const cityName = String(row.getCell(2).value || '').trim();
        if (!name) return;
        if (name === 'Downtown' && cityName === 'Cairo') return;
        if (zoneMap.has(name.toLowerCase())) {
          errors.push(`Zones row ${rowNumber}: "${name}" already exists — skipped`);
          return;
        }
        const cityId = cityMap.get(cityName.toLowerCase());
        if (!cityId) {
          errors.push(`Zones row ${rowNumber}: City "${cityName}" not found`);
          return;
        }
        zoneItems.push({ name, cityId });
      });

      for (const item of zoneItems) {
        try {
          const created = await this.prisma.zone.create({ data: item });
          zoneMap.set(created.name.toLowerCase(), created.id);
          imported++;
        } catch (err: any) {
          errors.push(`Failed zone "${item.name}": ${err.message}`);
        }
      }
    }

    // 5. Hotels
    const hotelsSheet = workbook.getWorksheet('Hotels');
    if (hotelsSheet) {
      const hotelItems: { name: string; zoneId: string; address?: string; stars?: number }[] = [];
      hotelsSheet.eachRow((row, rowNumber) => {
        if (rowNumber === 1) return;
        const name = String(row.getCell(1).value || '').trim();
        const zoneName = String(row.getCell(2).value || '').trim();
        const address = String(row.getCell(3).value || '').trim();
        const starsRaw = row.getCell(4).value;
        if (!name) return;
        if (name === 'Nile Hilton' && zoneName === 'Downtown') return;
        const zoneId = zoneMap.get(zoneName.toLowerCase());
        if (!zoneId) {
          errors.push(`Hotels row ${rowNumber}: Zone "${zoneName}" not found`);
          return;
        }
        let stars: number | undefined;
        if (starsRaw !== null && starsRaw !== undefined && String(starsRaw).trim() !== '') {
          stars = parseInt(String(starsRaw), 10);
          if (isNaN(stars) || stars < 1 || stars > 5) {
            errors.push(`Hotels row ${rowNumber}: Invalid stars value "${starsRaw}" (must be 1-5)`);
            return;
          }
        }
        hotelItems.push({
          name,
          zoneId,
          ...(address && { address }),
          ...(stars !== undefined && { stars }),
        });
      });

      for (const item of hotelItems) {
        try {
          await this.prisma.hotel.create({ data: item });
          imported++;
        } catch (err: any) {
          errors.push(`Failed hotel "${item.name}": ${err.message}`);
        }
      }
    }

    if (imported === 0 && errors.length === 0) {
      throw new BadRequestException('No data found in any location sheet');
    }

    return { imported, errors };
  }

  // ──────────────────────────────────────────────
  // UPDATE COORDINATES for a single location
  // ──────────────────────────────────────────────

  async updateLocationCoordinates(
    level: string,
    id: string,
    latitude: number,
    longitude: number,
    placeId?: string,
  ) {
    const data: any = { latitude, longitude };
    if (placeId) data.placeId = placeId;

    switch (level) {
      case 'country':
        return this.prisma.country.update({ where: { id }, data });
      case 'airport':
        return this.prisma.airport.update({ where: { id }, data });
      case 'city':
        return this.prisma.city.update({ where: { id }, data });
      case 'zone':
        return this.prisma.zone.update({ where: { id }, data });
      case 'hotel':
        return this.prisma.hotel.update({ where: { id }, data });
      default:
        throw new BadRequestException(`Unknown location level: ${level}`);
    }
  }

  // ──────────────────────────────────────────────
  // BATCH GEOCODE – resolve missing coordinates
  // ──────────────────────────────────────────────

  async batchGeocode(): Promise<{
    resolved: number;
    needsReview: Array<{ type: string; id: string; name: string; candidates: Array<{ placeId: string; name: string; formattedAddress: string; lat: number; lng: number }> }>;
  }> {
    let resolved = 0;
    const needsReview: Array<{ type: string; id: string; name: string; candidates: any[] }> = [];

    // Gather all locations without coordinates
    const [airports, cities, zones, hotels] = await Promise.all([
      this.prisma.airport.findMany({
        where: { deletedAt: null, latitude: null },
        select: { id: true, name: true, code: true },
      }),
      this.prisma.city.findMany({
        where: { deletedAt: null, latitude: null },
        select: { id: true, name: true },
      }),
      this.prisma.zone.findMany({
        where: { deletedAt: null, latitude: null },
        select: { id: true, name: true },
      }),
      this.prisma.hotel.findMany({
        where: { deletedAt: null, latitude: null },
        select: { id: true, name: true },
      }),
    ]);

    const items: Array<{ type: string; id: string; name: string; searchQuery: string; googleType?: string }> = [];

    for (const a of airports) {
      items.push({ type: 'airport', id: a.id, name: a.name, searchQuery: `${a.name} airport`, googleType: 'airport' });
    }
    for (const c of cities) {
      items.push({ type: 'city', id: c.id, name: c.name, searchQuery: `${c.name} city`, googleType: 'city' });
    }
    for (const z of zones) {
      items.push({ type: 'zone', id: z.id, name: z.name, searchQuery: z.name, googleType: 'zone' });
    }
    for (const h of hotels) {
      items.push({ type: 'hotel', id: h.id, name: h.name, searchQuery: h.name, googleType: 'hotel' });
    }

    for (const item of items) {
      try {
        const results = await this.geocoding.searchPlaces(item.searchQuery, item.googleType);

        if (results.length === 1) {
          // High confidence – auto-resolve
          const r = results[0];
          await this.updateLocationCoordinates(item.type, item.id, r.lat, r.lng, r.placeId);
          resolved++;
        } else if (results.length > 1) {
          // Ambiguous – flag for review
          needsReview.push({
            type: item.type,
            id: item.id,
            name: item.name,
            candidates: results.slice(0, 5),
          });
        }
        // else: no results found, skip
      } catch (err: any) {
        this.logger.warn(`Batch geocode failed for ${item.type} "${item.name}": ${err.message}`);
      }
    }

    return { resolved, needsReview };
  }
}
