import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import ExcelJS from 'exceljs';
import { PrismaService } from '../prisma/prisma.service.js';
import { UpsertTariffDto } from './dto/upsert-tariff.dto.js';
import type { Currency } from '../../generated/prisma/enums.js';

@Injectable()
export class DriverTariffsService {
  constructor(private readonly prisma: PrismaService) {}

  private readonly TARIFF_INCLUDE = {
    fromZone:       { select: { id: true, name: true } },
    toZone:         { select: { id: true, name: true } },
    fromAirport:    { select: { id: true, name: true, code: true } },
    toAirport:      { select: { id: true, name: true, code: true } },
    vehicleType:    { select: { id: true, name: true } },
    jobServiceType: { select: { id: true, name: true } },
  } as const;

  async findAll(filters: { fromZoneId?: string; toZoneId?: string; vehicleTypeId?: string }) {
    const where: Record<string, unknown> = {};
    if (filters.fromZoneId) where.fromZoneId = filters.fromZoneId;
    if (filters.toZoneId)   where.toZoneId   = filters.toZoneId;
    if (filters.vehicleTypeId) where.vehicleTypeId = filters.vehicleTypeId;

    return this.prisma.driverPriceTariff.findMany({
      where,
      include: this.TARIFF_INCLUDE,
      orderBy: [{ vehicleType: { name: 'asc' } }],
    });
  }

  async upsert(dto: UpsertTariffDto) {
    // Validate: must have exactly one from-location and one to-location
    if (!dto.fromZoneId && !dto.fromAirportId) {
      throw new BadRequestException('Either fromZoneId or fromAirportId is required');
    }
    if (!dto.toZoneId && !dto.toAirportId) {
      throw new BadRequestException('Either toZoneId or toAirportId is required');
    }

    // Find existing record (partial unique indexes — search manually)
    const existing = await this.prisma.driverPriceTariff.findFirst({
      where: {
        fromZoneId:    dto.fromZoneId    ?? null,
        toZoneId:      dto.toZoneId      ?? null,
        fromAirportId: dto.fromAirportId ?? null,
        toAirportId:   dto.toAirportId   ?? null,
        vehicleTypeId: dto.vehicleTypeId,
      },
    });

    const payload = {
      fromZoneId:    dto.fromZoneId    ?? null,
      toZoneId:      dto.toZoneId      ?? null,
      fromAirportId: dto.fromAirportId ?? null,
      toAirportId:   dto.toAirportId   ?? null,
      vehicleTypeId: dto.vehicleTypeId,
      amount:        dto.amount,
      currency:      (dto.currency as Currency) ?? 'EGP',
      notes:         dto.notes ?? null,
      isActive:      dto.isActive ?? true,
      jobServiceTypeId: dto.jobServiceTypeId ?? null,
    };

    if (existing) {
      return this.prisma.driverPriceTariff.update({
        where: { id: existing.id },
        data: {
          amount:          payload.amount,
          currency:        payload.currency,
          notes:           payload.notes,
          isActive:        payload.isActive,
          jobServiceTypeId: payload.jobServiceTypeId,
        },
        include: this.TARIFF_INCLUDE,
      });
    }

    return this.prisma.driverPriceTariff.create({
      data: payload,
      include: this.TARIFF_INCLUDE,
    });
  }

  async remove(id: string) {
    const existing = await this.prisma.driverPriceTariff.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException(`Driver tariff "${id}" not found`);
    return this.prisma.driverPriceTariff.delete({ where: { id } });
  }

  /**
   * Look up the best matching active tariff for a route.
   * Accepts nullable zone/airport IDs — tries all populated combos.
   */
  async lookup(
    fromZoneId: string | null | undefined,
    toZoneId: string | null | undefined,
    vehicleTypeId: string,
    fromAirportId?: string | null,
    toAirportId?: string | null,
  ) {
    // Build an OR of all non-null from+to combos that match the given locations
    const orClauses: any[] = [];

    if (fromZoneId && toZoneId) {
      orClauses.push({ fromZoneId, toZoneId: toZoneId, fromAirportId: null, toAirportId: null });
    }
    if (fromAirportId && toZoneId) {
      orClauses.push({ fromAirportId, toZoneId: toZoneId, fromZoneId: null, toAirportId: null });
    }
    if (fromZoneId && toAirportId) {
      orClauses.push({ fromZoneId, toAirportId, fromAirportId: null, toZoneId: null });
    }
    if (fromAirportId && toAirportId) {
      orClauses.push({ fromAirportId, toAirportId, fromZoneId: null, toZoneId: null });
    }

    if (orClauses.length === 0) return null;

    return this.prisma.driverPriceTariff.findFirst({
      where: { vehicleTypeId, isActive: true, OR: orClauses },
    });
  }

  /**
   * Build the DriverTripFee create-data for a completed job: airport-aware
   * tariff lookup keyed on the assigned vehicle's type. Returns null when the
   * job lacks a from+to pair. Amount falls back to 0 if no tariff matches.
   * Centralises what the dispatcher completion path does so the driver/rep
   * portals stop creating fees at amount 0.
   */
  async resolveJobTripFee(
    job: {
      fromZoneId?: string | null;
      toZoneId?: string | null;
      originAirportId?: string | null;
      destinationAirportId?: string | null;
    },
    vehicleId: string | null | undefined,
  ) {
    const fromZoneId = job.fromZoneId ?? null;
    const toZoneId = job.toZoneId ?? null;
    const fromAirportId = job.originAirportId ?? null;
    const toAirportId = job.destinationAirportId ?? null;
    if (!(fromZoneId || fromAirportId) || !(toZoneId || toAirportId)) return null;

    let vehicleTypeId: string | null = null;
    if (vehicleId) {
      const vehicle = await this.prisma.vehicle.findUnique({
        where: { id: vehicleId },
        select: { vehicleTypeId: true },
      });
      vehicleTypeId = vehicle?.vehicleTypeId ?? null;
    }

    let amount = 0;
    let tariffId: string | null = null;
    if (vehicleTypeId) {
      const tariff = await this.lookup(fromZoneId, toZoneId, vehicleTypeId, fromAirportId, toAirportId);
      if (tariff) {
        amount = Number(tariff.amount);
        tariffId = tariff.id;
      }
    }

    return {
      fromZoneId: fromZoneId ?? undefined,
      toZoneId: toZoneId ?? undefined,
      fromAirportId: fromAirportId ?? undefined,
      toAirportId: toAirportId ?? undefined,
      vehicleTypeId: vehicleTypeId ?? undefined,
      tariffId: tariffId ?? undefined,
      amount,
      tariffAmount: amount,
      currency: 'EGP' as const,
    };
  }

  // ─────────────────────────────────────────────────────
  // EXCEL TEMPLATE – generate downloadable template
  // ─────────────────────────────────────────────────────

  async generateTemplate(): Promise<Buffer> {
    const [zones, airports, vehicleTypes, serviceTypes] = await Promise.all([
      this.prisma.zone.findMany({ select: { id: true, name: true, city: { select: { name: true } } }, orderBy: { name: 'asc' } }),
      this.prisma.airport.findMany({ select: { id: true, name: true, code: true }, where: { isActive: true }, orderBy: { name: 'asc' } }),
      this.prisma.vehicleType.findMany({ select: { id: true, name: true }, where: { isActive: true }, orderBy: { name: 'asc' } }),
      this.prisma.jobServiceType.findMany({ select: { id: true, name: true }, where: { isActive: true }, orderBy: { name: 'asc' } }),
    ]);

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    // ── Instructions ──
    const inst = workbook.addWorksheet('Instructions');
    inst.columns = [{ width: 90 }];
    inst.addRow(['Driver Tariffs – Bulk Import Template']).font = { bold: true, size: 14 };
    inst.addRow(['']);
    inst.addRow(['Columns in the "Tariffs" sheet:']).font = { bold: true };
    inst.addRow(['1. From Location  – zone name OR airport code (e.g. HRG) — see "Zones" / "Airports" sheets']);
    inst.addRow(['2. To Location    – zone name OR airport code']);
    inst.addRow(['3. Vehicle Type   – exact name from "VehicleTypes" sheet']);
    inst.addRow(['4. Amount         – number, e.g. 150']);
    inst.addRow(['5. Currency       – EGP / USD / EUR / GBP / SAR  (default EGP)']);
    inst.addRow(['6. Service Type   – optional; exact name from "ServiceTypes" sheet']);
    inst.addRow(['7. Notes          – optional free text']);
    inst.addRow(['']);
    inst.addRow(['Rules:']).font = { bold: true };
    inst.addRow(['- Use airport CODE (e.g. HRG) for airports, zone NAME for zones']);
    inst.addRow(['- Duplicate from+to+vehicle rows UPDATE the existing tariff']);
    inst.addRow(['- Max 1 000 rows per import']);

    // ── Tariffs data sheet ──
    const sheet = workbook.addWorksheet('Tariffs');
    sheet.columns = [
      { header: 'From Location', key: 'from',         width: 25 },
      { header: 'To Location',   key: 'to',           width: 25 },
      { header: 'Vehicle Type',  key: 'vehicleType',  width: 20 },
      { header: 'Amount',        key: 'amount',       width: 14 },
      { header: 'Currency',      key: 'currency',     width: 12 },
      { header: 'Service Type',  key: 'serviceType',  width: 25 },
      { header: 'Notes',         key: 'notes',        width: 30 },
    ];
    const hdr = sheet.getRow(1);
    hdr.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    hdr.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF4472C4' } };
    hdr.alignment = { vertical: 'middle', horizontal: 'center' };
    hdr.height = 22;

    // Sample rows: zone→zone and airport→zone
    const samples = [
      { from: zones[0]?.name ?? 'Zone A',           to: zones[1]?.name ?? 'Zone B',           vehicleType: vehicleTypes[0]?.name ?? 'Sedan', amount: 150, currency: 'EGP', serviceType: serviceTypes[0]?.name ?? '', notes: '' },
      { from: airports[0]?.code ?? 'HRG',           to: zones[0]?.name ?? 'Zone A',           vehicleType: vehicleTypes[0]?.name ?? 'Sedan', amount: 200, currency: 'EGP', serviceType: '', notes: 'Airport pickup' },
      { from: zones[0]?.name ?? 'Zone A',           to: airports[0]?.code ?? 'HRG',           vehicleType: vehicleTypes[0]?.name ?? 'Sedan', amount: 200, currency: 'EGP', serviceType: '', notes: 'Airport drop-off' },
    ];
    for (const s of samples) {
      const r = sheet.addRow(s);
      r.font = { italic: true, color: { argb: 'FF999999' } };
    }

    // ── Zones lookup ──
    const zSheet = workbook.addWorksheet('Zones');
    zSheet.columns = [{ header: 'Zone Name', key: 'name', width: 30 }, { header: 'City', key: 'city', width: 25 }];
    zSheet.getRow(1).font = { bold: true };
    for (const z of zones) zSheet.addRow({ name: z.name, city: z.city?.name ?? '' });

    // ── Airports lookup ──
    const aSheet = workbook.addWorksheet('Airports');
    aSheet.columns = [{ header: 'Airport Code', key: 'code', width: 15 }, { header: 'Airport Name', key: 'name', width: 40 }];
    aSheet.getRow(1).font = { bold: true };
    for (const a of airports) aSheet.addRow({ code: a.code, name: a.name });

    // ── VehicleTypes lookup ──
    const vtSheet = workbook.addWorksheet('VehicleTypes');
    vtSheet.columns = [{ header: 'Vehicle Type Name', key: 'name', width: 30 }];
    vtSheet.getRow(1).font = { bold: true };
    for (const vt of vehicleTypes) vtSheet.addRow({ name: vt.name });

    // ── ServiceTypes lookup ──
    const stSheet = workbook.addWorksheet('ServiceTypes');
    stSheet.columns = [{ header: 'Service Type Name', key: 'name', width: 30 }];
    stSheet.getRow(1).font = { bold: true };
    for (const st of serviceTypes) stSheet.addRow({ name: st.name });

    const buf = await workbook.xlsx.writeBuffer();
    return Buffer.from(buf);
  }

  // ─────────────────────────────────────────────────────
  // EXCEL IMPORT – parse & upsert tariffs
  // ─────────────────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const sheet = workbook.getWorksheet('Tariffs');
    if (!sheet) throw new BadRequestException('Invalid file: "Tariffs" sheet not found. Use the downloaded template.');

    const [zones, airports, vehicleTypes, serviceTypes] = await Promise.all([
      this.prisma.zone.findMany({ select: { id: true, name: true } }),
      this.prisma.airport.findMany({ select: { id: true, name: true, code: true } }),
      this.prisma.vehicleType.findMany({ select: { id: true, name: true } }),
      this.prisma.jobServiceType.findMany({ select: { id: true, name: true } }),
    ]);

    const zoneMap    = new Map(zones.map((z) => [z.name.trim().toLowerCase(), z.id]));
    const airportMap = new Map(airports.map((a) => [a.code.trim().toUpperCase(), a.id]));
    const vtMap      = new Map(vehicleTypes.map((v) => [v.name.trim().toLowerCase(), v.id]));
    const stMap      = new Map(serviceTypes.map((s) => [s.name.trim().toLowerCase(), s.id]));
    const validCurrencies = new Set(['EGP', 'USD', 'EUR', 'GBP', 'SAR']);

    const rows: UpsertTariffDto[] = [];
    const errors: string[] = [];

    // Helper: resolve a location cell — airport code takes precedence over zone name
    const resolveLocation = (raw: string, rowNumber: number, label: string): { zoneId?: string; airportId?: string } | null => {
      const upper = raw.trim().toUpperCase();
      const lower = raw.trim().toLowerCase();
      if (!raw.trim()) return null;
      const airportId = airportMap.get(upper);
      if (airportId) return { airportId };
      const zoneId = zoneMap.get(lower);
      if (zoneId) return { zoneId };
      errors.push(`Row ${rowNumber}: ${label} "${raw}" not found as airport code or zone name`);
      return null;
    };

    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const fromRaw         = String(row.getCell(1).value ?? '').trim();
      const toRaw           = String(row.getCell(2).value ?? '').trim();
      const vehicleTypeName = String(row.getCell(3).value ?? '').trim();
      const amountRaw       = row.getCell(4).value;
      const currencyRaw     = String(row.getCell(5).value ?? 'EGP').trim().toUpperCase();
      const serviceTypeName = String(row.getCell(6).value ?? '').trim();
      const notes           = String(row.getCell(7).value ?? '').trim();

      if (!fromRaw && !toRaw && !vehicleTypeName) return; // blank row

      if (!fromRaw) { errors.push(`Row ${rowNumber}: "From Location" is required`); return; }
      if (!toRaw)   { errors.push(`Row ${rowNumber}: "To Location" is required`); return; }
      if (!vehicleTypeName) { errors.push(`Row ${rowNumber}: "Vehicle Type" is required`); return; }

      const from = resolveLocation(fromRaw, rowNumber, 'From Location');
      if (!from) return;
      const to = resolveLocation(toRaw, rowNumber, 'To Location');
      if (!to) return;

      const vehicleTypeId = vtMap.get(vehicleTypeName.toLowerCase());
      if (!vehicleTypeId) { errors.push(`Row ${rowNumber}: Vehicle type "${vehicleTypeName}" not found`); return; }

      const amount = parseFloat(String(amountRaw ?? ''));
      if (isNaN(amount) || amount < 0) { errors.push(`Row ${rowNumber}: Invalid amount "${amountRaw}"`); return; }

      const currency = currencyRaw || 'EGP';
      if (!validCurrencies.has(currency)) { errors.push(`Row ${rowNumber}: Invalid currency "${currency}"`); return; }

      let jobServiceTypeId: string | undefined;
      if (serviceTypeName) {
        jobServiceTypeId = stMap.get(serviceTypeName.toLowerCase());
        if (!jobServiceTypeId) { errors.push(`Row ${rowNumber}: Service type "${serviceTypeName}" not found`); return; }
      }

      rows.push({
        fromZoneId:    from.zoneId,
        fromAirportId: from.airportId,
        toZoneId:      to.zoneId,
        toAirportId:   to.airportId,
        vehicleTypeId, amount, currency,
        notes: notes || undefined,
        jobServiceTypeId,
      });
    });

    if (rows.length === 0 && errors.length === 0) throw new BadRequestException('No data rows found in the "Tariffs" sheet');
    if (rows.length > 1000) throw new BadRequestException('Maximum 1 000 rows per import');

    let imported = 0;
    for (const dto of rows) {
      try {
        await this.upsert(dto);
        imported++;
      } catch (err: any) {
        errors.push(`Row "${dto.fromZoneId ?? dto.fromAirportId}"→"${dto.toZoneId ?? dto.toAirportId}": ${err.message}`);
      }
    }

    return { imported, errors };
  }
}
