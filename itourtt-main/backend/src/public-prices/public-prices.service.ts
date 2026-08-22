import { Injectable, NotFoundException } from '@nestjs/common';
import ExcelJS from 'exceljs';
import { PrismaService } from '../prisma/prisma.service.js';
import { UpsertPublicPricesDto, PublicPriceItemDto } from './dto/upsert-public-prices.dto.js';
import type { ServiceType, Currency, TransferType } from '../../generated/prisma/enums.js';

const INCLUDE = {
  fromZone: true,
  toZone: true,
  vehicleType: true,
} as const;

@Injectable()
export class PublicPricesService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(filters: {
    serviceType?: string;
    transferType?: string;
    fromZoneId?: string;
    toZoneId?: string;
    vehicleTypeId?: string;
  }) {
    const where: Record<string, unknown> = {};
    if (filters.serviceType)  where.serviceType  = filters.serviceType  as ServiceType;
    if (filters.transferType) where.transferType = filters.transferType as TransferType;
    if (filters.fromZoneId)   where.fromZoneId   = filters.fromZoneId;
    if (filters.toZoneId)     where.toZoneId     = filters.toZoneId;
    if (filters.vehicleTypeId) where.vehicleTypeId = filters.vehicleTypeId;

    return this.prisma.publicPriceItem.findMany({
      where,
      include: INCLUDE,
      orderBy: [{ serviceType: 'asc' }, { fromZone: { name: 'asc' } }],
    });
  }

  async bulkUpsert(dto: UpsertPublicPricesDto) {
    return this.prisma.$transaction(async (tx) => {
      const results: any[] = [];
      for (const item of dto.items) {
        const result = await tx.publicPriceItem.upsert({
          where: {
            serviceType_transferType_fromZoneId_toZoneId_vehicleTypeId: {
              serviceType:  item.serviceType  as ServiceType,
              transferType: (item.transferType ?? 'PRIVATE') as TransferType,
              fromZoneId:   item.fromZoneId,
              toZoneId:     item.toZoneId,
              vehicleTypeId: item.vehicleTypeId,
            },
          },
          update: {
            price:            item.price,
            driverTip:        item.driverTip        ?? 0,
            boosterSeatPrice: item.boosterSeatPrice  ?? 0,
            babySeatPrice:    item.babySeatPrice     ?? 0,
            wheelChairPrice:  item.wheelChairPrice   ?? 0,
            currency:         (item.currency as Currency) || 'EGP',
          },
          create: {
            serviceType:      item.serviceType  as ServiceType,
            transferType:     (item.transferType ?? 'PRIVATE') as TransferType,
            fromZoneId:       item.fromZoneId,
            toZoneId:         item.toZoneId,
            vehicleTypeId:    item.vehicleTypeId,
            price:            item.price,
            driverTip:        item.driverTip        ?? 0,
            boosterSeatPrice: item.boosterSeatPrice  ?? 0,
            babySeatPrice:    item.babySeatPrice     ?? 0,
            wheelChairPrice:  item.wheelChairPrice   ?? 0,
            currency:         (item.currency as Currency) || 'EGP',
          },
          include: INCLUDE,
        });
        results.push(result);
      }
      return results;
    });
  }

  async updateOne(id: string, item: Partial<PublicPriceItemDto>) {
    const existing = await this.prisma.publicPriceItem.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException(`Public price item "${id}" not found`);

    return this.prisma.publicPriceItem.update({
      where: { id },
      data: {
        ...(item.serviceType  && { serviceType:  item.serviceType  as ServiceType }),
        ...(item.transferType && { transferType: item.transferType as TransferType }),
        ...(item.fromZoneId   && { fromZoneId:   item.fromZoneId }),
        ...(item.toZoneId     && { toZoneId:     item.toZoneId }),
        ...(item.vehicleTypeId && { vehicleTypeId: item.vehicleTypeId }),
        ...(item.price !== undefined && { price: item.price }),
        ...(item.driverTip !== undefined && { driverTip: item.driverTip }),
        ...(item.currency  && { currency: item.currency as Currency }),
      },
      include: INCLUDE,
    });
  }

  async remove(id: string) {
    const existing = await this.prisma.publicPriceItem.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException(`Public price item "${id}" not found`);
    return this.prisma.publicPriceItem.delete({ where: { id } });
  }

  async buildImportTemplate(): Promise<Buffer> {
    const [zones, vehicleTypes] = await Promise.all([
      this.prisma.zone.findMany({ where: { deletedAt: null }, orderBy: { name: 'asc' }, select: { name: true } }),
      this.prisma.vehicleType.findMany({ where: { isActive: true }, orderBy: { name: 'asc' }, select: { name: true } }),
    ]);

    const zoneNames   = zones.map((z) => z.name);
    const vtypeNames  = vehicleTypes.map((v) => v.name);
    const currencies  = ['EGP', 'USD', 'EUR', 'GBP', 'SAR'];

    const wb = new ExcelJS.Workbook();

    // ── Reference sheet (hidden) ──────────────────────────────
    const refSheet = wb.addWorksheet('_Reference');
    refSheet.state = 'veryHidden';
    refSheet.getColumn(1).header = 'Zones';
    refSheet.getColumn(2).header = 'Car Types';
    refSheet.getColumn(3).header = 'Currencies';
    zoneNames.forEach((n, i)  => { refSheet.getCell(i + 2, 1).value = n; });
    vtypeNames.forEach((n, i) => { refSheet.getCell(i + 2, 2).value = n; });
    currencies.forEach((c, i) => { refSheet.getCell(i + 2, 3).value = c; });

    const zoneEnd   = zoneNames.length  + 1;
    const vtypeEnd  = vtypeNames.length + 1;
    const curEnd    = currencies.length + 1;

    // ── Prices sheet ─────────────────────────────────────────
    const ws = wb.addWorksheet('Prices');
    ws.views = [{ state: 'frozen', ySplit: 1 }];

    const COL = {
      service_type:  { header: 'service_type*',  key: 'A', width: 16 },
      transfer_type: { header: 'transfer_type*', key: 'B', width: 14 },
      from_zone:     { header: 'from_zone*',     key: 'C', width: 28 },
      to_zone:       { header: 'to_zone*',       key: 'D', width: 28 },
      car_type:      { header: 'car_type*',      key: 'E', width: 20 },
      price:         { header: 'price*',         key: 'F', width: 12 },
      currency:      { header: 'currency',       key: 'G', width: 10 },
    };

    const headerRow = ws.getRow(1);
    Object.entries(COL).forEach(([, col], i) => {
      const cell = headerRow.getCell(i + 1);
      cell.value = col.header;
      cell.font  = { bold: true, color: { argb: 'FFFFFFFF' } };
      cell.fill  = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF2563EB' } };
      cell.alignment = { horizontal: 'center' };
      ws.getColumn(i + 1).width = col.width;
    });
    headerRow.height = 22;

    // 2 example rows
    const examples = [
      ['ARR', 'PRIVATE', zoneNames[0] ?? 'Zone A', zoneNames[1] ?? 'Zone B', vtypeNames[0] ?? 'Sedan', 100, 'EGP'],
      ['DEP', 'SHARED',  zoneNames[1] ?? 'Zone B', zoneNames[0] ?? 'Zone A', vtypeNames[0] ?? 'Sedan', 120, 'USD'],
    ];
    examples.forEach((ex, i) => {
      const row = ws.getRow(i + 2);
      ex.forEach((val, j) => {
        row.getCell(j + 1).value = val;
        row.getCell(j + 1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDBEAFE' } };
      });
    });

    // ── Data validations ──────────────────────────────────────
    const DATA_ROWS = 1000;
    const dv = (ws as any).dataValidations;

    // service_type — inline list
    dv.add(`A2:A${DATA_ROWS}`, {
      type: 'list',
      allowBlank: false,
      formulae: ['"ARR,DEP"'],
      showErrorMessage: true,
      errorTitle: 'Invalid value',
      error: 'Please select ARR or DEP',
    });

    // transfer_type — inline list
    dv.add(`B2:B${DATA_ROWS}`, {
      type: 'list',
      allowBlank: false,
      formulae: ['"PRIVATE,SHARED"'],
      showErrorMessage: true,
      errorTitle: 'Invalid value',
      error: 'Please select PRIVATE or SHARED',
    });

    // from_zone — reference sheet
    dv.add(`C2:C${DATA_ROWS}`, {
      type: 'list',
      allowBlank: false,
      formulae: [`_Reference!$A$2:$A$${zoneEnd}`],
      showErrorMessage: true,
      errorTitle: 'Unknown zone',
      error: 'Select a zone from the list',
    });

    // to_zone — reference sheet
    dv.add(`D2:D${DATA_ROWS}`, {
      type: 'list',
      allowBlank: false,
      formulae: [`_Reference!$A$2:$A$${zoneEnd}`],
      showErrorMessage: true,
      errorTitle: 'Unknown zone',
      error: 'Select a zone from the list',
    });

    // car_type — reference sheet
    dv.add(`E2:E${DATA_ROWS}`, {
      type: 'list',
      allowBlank: false,
      formulae: [`_Reference!$B$2:$B$${vtypeEnd}`],
      showErrorMessage: true,
      errorTitle: 'Unknown car type',
      error: 'Select a car type from the list',
    });

    // price — decimal ≥ 0
    dv.add(`F2:F${DATA_ROWS}`, {
      type: 'decimal',
      operator: 'greaterThanOrEqual',
      allowBlank: false,
      formulae: [0],
      showErrorMessage: true,
      errorTitle: 'Invalid price',
      error: 'Price must be a positive number',
    });

    // currency — reference sheet
    dv.add(`G2:G${DATA_ROWS}`, {
      type: 'list',
      allowBlank: true,
      formulae: [`_Reference!$C$2:$C$${curEnd}`],
      showErrorMessage: true,
      errorTitle: 'Invalid currency',
      error: 'Select a currency from the list',
    });

    const buf = await wb.xlsx.writeBuffer();
    return Buffer.from(buf);
  }
}
