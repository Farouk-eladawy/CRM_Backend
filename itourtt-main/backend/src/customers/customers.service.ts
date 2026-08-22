import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import ExcelJS from 'exceljs';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateCustomerDto } from './dto/create-customer.dto.js';
import { UpdateCustomerDto } from './dto/update-customer.dto.js';
import { BulkPriceListDto, PriceItemDto } from './dto/price-list.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { PaginatedResponse } from '../common/dto/api-response.dto.js';
import type { Currency, ServiceType } from '../../generated/prisma/enums.js';
import { SELECTABLE_SERVICE_TYPES, SERVICE_TYPE_LABEL_PAIRS } from '../common/utils/service-type.util.js';

const VALID_SERVICE_TYPES = new Set<string>(SELECTABLE_SERVICE_TYPES);

const SERVICE_TYPE_LABELS: [string, string][] = SERVICE_TYPE_LABEL_PAIRS;

@Injectable()
export class CustomersService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(pagination: PaginationDto, search?: string) {
    const { page = 1, limit = 20 } = pagination;
    const skip = (page - 1) * limit;

    const where: Record<string, unknown> = { deletedAt: null };

    if (search) {
      where.OR = [
        { legalName: { contains: search, mode: 'insensitive' } },
        { tradeName: { contains: search, mode: 'insensitive' } },
      ];
    }

    const [data, total] = await Promise.all([
      this.prisma.customer.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.customer.count({ where }),
    ]);

    return new PaginatedResponse(data, total, page, limit);
  }

  async findOne(id: string) {
    const customer = await this.prisma.customer.findFirst({
      where: { id, deletedAt: null },
    });

    if (!customer) {
      throw new NotFoundException(`Customer with ID "${id}" not found`);
    }

    return customer;
  }

  async create(dto: CreateCustomerDto) {
    return this.prisma.customer.create({
      data: {
        legalName: dto.legalName,
        tradeName: dto.tradeName,
        taxId: dto.taxId,
        address: dto.address,
        city: dto.city,
        country: dto.country,
        phone: dto.phone,
        email: dto.email,
        contactPerson: dto.contactPerson,
        ...(dto.currency && { currency: dto.currency as Currency }),
        ...(dto.creditLimit !== undefined && { creditLimit: dto.creditLimit }),
        ...(dto.creditDays !== undefined && { creditDays: dto.creditDays }),
      },
    });
  }

  async update(id: string, dto: UpdateCustomerDto) {
    await this.findOne(id);

    return this.prisma.customer.update({
      where: { id },
      data: {
        ...(dto.legalName !== undefined && { legalName: dto.legalName }),
        ...(dto.tradeName !== undefined && { tradeName: dto.tradeName }),
        ...(dto.taxId !== undefined && { taxId: dto.taxId }),
        ...(dto.address !== undefined && { address: dto.address }),
        ...(dto.city !== undefined && { city: dto.city }),
        ...(dto.country !== undefined && { country: dto.country }),
        ...(dto.phone !== undefined && { phone: dto.phone }),
        ...(dto.email !== undefined && { email: dto.email }),
        ...(dto.contactPerson !== undefined && { contactPerson: dto.contactPerson }),
        ...(dto.currency !== undefined && { currency: dto.currency as Currency }),
        ...(dto.creditLimit !== undefined && { creditLimit: dto.creditLimit }),
        ...(dto.creditDays !== undefined && { creditDays: dto.creditDays }),
      },
    });
  }

  async toggleStatus(id: string) {
    const customer = await this.findOne(id);

    return this.prisma.customer.update({
      where: { id },
      data: { isActive: !customer.isActive },
    });
  }

  async remove(id: string) {
    await this.findOne(id);

    return this.prisma.customer.update({
      where: { id },
      data: { deletedAt: new Date() },
    });
  }

  async bulkDelete(ids: string[]) {
    if (!ids || ids.length === 0) {
      throw new BadRequestException('No customer IDs provided');
    }

    const result = await this.prisma.customer.updateMany({
      where: { id: { in: ids }, deletedAt: null },
      data: { deletedAt: new Date() },
    });

    return { deleted: result.count };
  }

  // Price List Methods

  async getPriceList(customerId: string) {
    await this.findOne(customerId);

    const priceItems = await this.prisma.customerPriceItem.findMany({
      where: { customerId },
      include: {
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
        vehicleType: { select: { id: true, name: true, seatCapacity: true } },
      },
      orderBy: [
        { serviceType: 'asc' },
        { fromZone: { name: 'asc' } },
        { toZone: { name: 'asc' } },
        { vehicleType: { seatCapacity: 'asc' } },
      ],
    });

    return priceItems;
  }

  async upsertPriceItems(customerId: string, dto: BulkPriceListDto) {
    await this.findOne(customerId);

    const results = await this.prisma.$transaction(
      dto.items.map((item: PriceItemDto) =>
        this.prisma.customerPriceItem.upsert({
          where: {
            customerId_serviceType_fromZoneId_toZoneId_vehicleTypeId: {
              customerId,
              serviceType: item.serviceType as ServiceType,
              fromZoneId: item.fromZoneId,
              toZoneId: item.toZoneId,
              vehicleTypeId: item.vehicleTypeId,
            },
          },
          create: {
            customerId,
            serviceType: item.serviceType as ServiceType,
            fromZoneId: item.fromZoneId,
            toZoneId: item.toZoneId,
            vehicleTypeId: item.vehicleTypeId,
            transferPrice: item.transferPrice,
            driverTip: item.driverTip,
            effectiveFrom: item.effectiveFrom ? new Date(item.effectiveFrom) : null,
            effectiveTo: item.effectiveTo ? new Date(item.effectiveTo) : null,
          },
          update: {
            transferPrice: item.transferPrice,
            driverTip: item.driverTip,
            effectiveFrom: item.effectiveFrom ? new Date(item.effectiveFrom) : null,
            effectiveTo: item.effectiveTo ? new Date(item.effectiveTo) : null,
          },
        }),
      ),
    );

    return results;
  }

  async deletePriceItem(customerId: string, priceItemId: string) {
    await this.findOne(customerId);

    const priceItem = await this.prisma.customerPriceItem.findFirst({
      where: { id: priceItemId, customerId },
    });

    if (!priceItem) {
      throw new NotFoundException(`Price item with ID "${priceItemId}" not found for this customer`);
    }

    return this.prisma.customerPriceItem.delete({
      where: { id: priceItemId },
    });
  }

  async getPriceForJob(
    customerId: string,
    serviceType: string,
    fromZoneId: string,
    toZoneId: string,
    vehicleTypeId: string,
  ) {
    const priceItem = await this.prisma.customerPriceItem.findFirst({
      where: {
        customerId,
        serviceType: serviceType as ServiceType,
        fromZoneId,
        toZoneId,
        vehicleTypeId,
        OR: [
          { effectiveFrom: null },
          { effectiveFrom: { lte: new Date() } },
        ],
        AND: [
          {
            OR: [
              { effectiveTo: null },
              { effectiveTo: { gte: new Date() } },
            ],
          },
        ],
      },
    });

    return priceItem;
  }

  // Excel Template & Import Methods

  async generatePriceListTemplate(): Promise<Buffer> {
    // Fetch all zones and vehicle types for the template
    const [zones, vehicleTypes] = await Promise.all([
      this.prisma.zone.findMany({
        select: { id: true, name: true },
        orderBy: { name: 'asc' },
      }),
      this.prisma.vehicleType.findMany({
        where: { isActive: true },
        select: { id: true, name: true, seatCapacity: true },
        orderBy: { seatCapacity: 'asc' },
      }),
    ]);

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    // Instructions sheet
    const instructionsSheet = workbook.addWorksheet('Instructions');
    instructionsSheet.columns = [{ width: 80 }];
    instructionsSheet.addRow(['Customer Price List Import Template']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Instructions:']);
    instructionsSheet.addRow(['1. Use the "Price List" sheet to enter your prices']);
    instructionsSheet.addRow(['2. Service Type must match exactly with codes from the "Service Types" sheet']);
    instructionsSheet.addRow(['3. From Zone and To Zone must match exactly with zone names from the "Zones" sheet']);
    instructionsSheet.addRow(['4. Vehicle Type must match exactly with names from the "Vehicle Types" sheet']);
    instructionsSheet.addRow(['5. Transfer Price and Driver Tip should be numeric values']);
    instructionsSheet.addRow(['6. Leave cells empty (or 0) for routes/vehicles you don\'t want to price']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Note: Existing prices for the same service type+route+vehicle combination will be updated']);
    instructionsSheet.getRow(1).font = { bold: true, size: 14 };
    instructionsSheet.getRow(3).font = { bold: true };

    // Price List sheet (main data entry)
    const priceSheet = workbook.addWorksheet('Price List');
    priceSheet.columns = [
      { header: 'Service Type', key: 'serviceType', width: 25 },
      { header: 'From Zone', key: 'fromZone', width: 25 },
      { header: 'To Zone', key: 'toZone', width: 25 },
      { header: 'Vehicle Type', key: 'vehicleType', width: 20 },
      { header: 'Transfer Price', key: 'transferPrice', width: 15 },
      { header: 'Driver Tip', key: 'driverTip', width: 15 },
    ];

    // Style header row
    priceSheet.getRow(1).font = { bold: true };
    priceSheet.getRow(1).fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF4472C4' },
    };
    priceSheet.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } };

    // Add sample rows
    if (zones.length >= 2 && vehicleTypes.length >= 1) {
      priceSheet.addRow({
        serviceType: 'ARR',
        fromZone: zones[0].name,
        toZone: zones[1].name,
        vehicleType: vehicleTypes[0].name,
        transferPrice: 0,
        driverTip: 0,
      });
    }

    // Zones reference sheet
    const zonesSheet = workbook.addWorksheet('Zones');
    zonesSheet.columns = [
      { header: 'Zone ID', key: 'id', width: 40 },
      { header: 'Zone Name', key: 'name', width: 30 },
    ];
    zonesSheet.getRow(1).font = { bold: true };
    zones.forEach((zone) => {
      zonesSheet.addRow({ id: zone.id, name: zone.name });
    });

    // Vehicle Types reference sheet
    const vehicleTypesSheet = workbook.addWorksheet('Vehicle Types');
    vehicleTypesSheet.columns = [
      { header: 'Vehicle Type ID', key: 'id', width: 40 },
      { header: 'Vehicle Type Name', key: 'name', width: 25 },
      { header: 'Seat Capacity', key: 'seatCapacity', width: 15 },
    ];
    vehicleTypesSheet.getRow(1).font = { bold: true };
    vehicleTypes.forEach((vt) => {
      vehicleTypesSheet.addRow({ id: vt.id, name: vt.name, seatCapacity: vt.seatCapacity });
    });

    // Service Types reference sheet
    const serviceTypesSheet = workbook.addWorksheet('Service Types');
    serviceTypesSheet.columns = [
      { header: 'Service Type Code', key: 'code', width: 30 },
      { header: 'Description', key: 'description', width: 40 },
    ];
    serviceTypesSheet.getRow(1).font = { bold: true };
    SERVICE_TYPE_LABELS.forEach(([code, desc]) => {
      serviceTypesSheet.addRow({ code, description: desc });
    });

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  // ──────────────────────────────────────────────
  // EXPORT – all customers to Excel
  // ──────────────────────────────────────────────

  async exportToExcel(): Promise<Buffer> {
    const customers = await this.prisma.customer.findMany({
      where: { deletedAt: null },
      orderBy: { legalName: 'asc' },
    });

    const rows = customers.map((c) => ({
      'Legal Name': c.legalName,
      'Trade Name': c.tradeName || '',
      'Tax ID': c.taxId || '',
      Address: c.address || '',
      City: c.city || '',
      Country: c.country || '',
      Phone: c.phone || '',
      Email: c.email || '',
      'Contact Person': c.contactPerson || '',
      Currency: c.currency,
      'Credit Limit': c.creditLimit ? Number(c.creditLimit) : '',
      'Credit Days': c.creditDays ?? '',
      Status: c.isActive ? 'Active' : 'Inactive',
    }));

    const ws = XLSX.utils.json_to_sheet(rows);
    const colWidths = Object.keys(rows[0] || {}).map((key) => {
      const maxLen = Math.max(key.length, ...rows.map((r) => String((r as any)[key] || '').length));
      return { wch: Math.min(maxLen + 2, 40) };
    });
    ws['!cols'] = colWidths;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Customers');
    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  async generateImportTemplate(): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    const instructionsSheet = workbook.addWorksheet('Instructions');
    instructionsSheet.columns = [{ width: 80 }];
    instructionsSheet.addRow(['Customer Bulk Import Template']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Instructions:']);
    instructionsSheet.addRow(['1. Fill in customer data in the "Customers" sheet']);
    instructionsSheet.addRow(['2. Legal Name is the only required field']);
    instructionsSheet.addRow(['3. Currency must be one of: EGP, USD, EUR, GBP, SAR (defaults to EGP)']);
    instructionsSheet.addRow(['4. Credit Limit and Credit Days are optional numeric values']);
    instructionsSheet.addRow(['5. Do not modify column headers']);
    instructionsSheet.addRow(['6. Save the file and upload it via the import button']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Notes:']);
    instructionsSheet.addRow(['- All imported customers will be set to Active status']);
    instructionsSheet.addRow(['- Maximum 500 customers per import']);
    instructionsSheet.getRow(1).font = { bold: true, size: 14 };
    instructionsSheet.getRow(3).font = { bold: true };
    instructionsSheet.getRow(11).font = { bold: true };

    const customersSheet = workbook.addWorksheet('Customers');
    customersSheet.columns = [
      { header: 'Legal Name', key: 'legalName', width: 30 },
      { header: 'Trade Name', key: 'tradeName', width: 25 },
      { header: 'Tax ID', key: 'taxId', width: 20 },
      { header: 'Address', key: 'address', width: 30 },
      { header: 'City', key: 'city', width: 20 },
      { header: 'Country', key: 'country', width: 20 },
      { header: 'Phone', key: 'phone', width: 20 },
      { header: 'Email', key: 'email', width: 25 },
      { header: 'Contact Person', key: 'contactPerson', width: 20 },
      { header: 'Currency', key: 'currency', width: 12 },
      { header: 'Credit Limit', key: 'creditLimit', width: 15 },
      { header: 'Credit Days', key: 'creditDays', width: 15 },
    ];

    const headerRow = customersSheet.getRow(1);
    headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF4472C4' } };
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' };

    customersSheet.addRow({
      legalName: 'Cairo Tours Agency', tradeName: 'Cairo Tours', taxId: '987-654-321',
      address: '5 Tahrir St', city: 'Cairo', country: 'Egypt',
      phone: '+20 2 9876 5432', email: 'info@cairotours.com',
      contactPerson: 'Ahmed Mahmoud', currency: 'EGP', creditLimit: 100000, creditDays: 45,
    });
    customersSheet.addRow({
      legalName: 'Desert Safari Co', tradeName: '', taxId: '', address: '', city: '', country: '',
      phone: '', email: '', contactPerson: '', currency: 'USD', creditLimit: '', creditDays: '',
    });

    for (let i = 2; i <= 3; i++) {
      customersSheet.getRow(i).font = { italic: true, color: { argb: 'FF999999' } };
    }

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const customersSheet = workbook.getWorksheet('Customers');
    if (!customersSheet) {
      throw new BadRequestException('Invalid template: "Customers" sheet not found');
    }

    const validCurrencies = new Set(['EGP', 'USD', 'EUR', 'GBP', 'SAR']);
    const items: {
      legalName: string; tradeName?: string; taxId?: string; address?: string;
      city?: string; country?: string; phone?: string; email?: string;
      contactPerson?: string; currency: string; creditLimit?: number; creditDays?: number;
    }[] = [];
    const errors: string[] = [];

    customersSheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;

      const legalName = String(row.getCell(1).value || '').trim();
      if (!legalName) return;

      // Skip sample rows
      if (legalName === 'Cairo Tours Agency' || legalName === 'Desert Safari Co') return;

      const tradeName = String(row.getCell(2).value || '').trim();
      const taxId = String(row.getCell(3).value || '').trim();
      const address = String(row.getCell(4).value || '').trim();
      const city = String(row.getCell(5).value || '').trim();
      const country = String(row.getCell(6).value || '').trim();
      const phone = String(row.getCell(7).value || '').trim();
      const email = String(row.getCell(8).value || '').trim();
      const contactPerson = String(row.getCell(9).value || '').trim();
      const currency = String(row.getCell(10).value || 'EGP').trim().toUpperCase();
      const creditLimitRaw = row.getCell(11).value;
      const creditDaysRaw = row.getCell(12).value;

      if (!validCurrencies.has(currency)) {
        errors.push(`Row ${rowNumber}: Invalid currency "${currency}"`);
        return;
      }

      let creditLimit: number | undefined;
      if (creditLimitRaw !== null && creditLimitRaw !== undefined && String(creditLimitRaw).trim() !== '') {
        creditLimit = parseFloat(String(creditLimitRaw));
        if (isNaN(creditLimit) || creditLimit < 0) {
          errors.push(`Row ${rowNumber}: Invalid credit limit`);
          return;
        }
      }

      let creditDays: number | undefined;
      if (creditDaysRaw !== null && creditDaysRaw !== undefined && String(creditDaysRaw).trim() !== '') {
        creditDays = parseInt(String(creditDaysRaw), 10);
        if (isNaN(creditDays) || creditDays < 0) {
          errors.push(`Row ${rowNumber}: Invalid credit days`);
          return;
        }
      }

      items.push({
        legalName,
        ...(tradeName && { tradeName }),
        ...(taxId && { taxId }),
        ...(address && { address }),
        ...(city && { city }),
        ...(country && { country }),
        ...(phone && { phone }),
        ...(email && { email }),
        ...(contactPerson && { contactPerson }),
        currency,
        ...(creditLimit !== undefined && { creditLimit }),
        ...(creditDays !== undefined && { creditDays }),
      });
    });

    if (items.length === 0 && errors.length === 0) {
      throw new BadRequestException('No data found in the Customers sheet');
    }

    if (items.length > 500) {
      throw new BadRequestException('Maximum 500 customers per import.');
    }

    let imported = 0;
    for (const item of items) {
      try {
        await this.prisma.customer.create({
          data: {
            legalName: item.legalName,
            tradeName: item.tradeName,
            taxId: item.taxId,
            address: item.address,
            city: item.city,
            country: item.country,
            phone: item.phone,
            email: item.email,
            contactPerson: item.contactPerson,
            currency: item.currency as Currency,
            creditLimit: item.creditLimit,
            creditDays: item.creditDays,
          },
        });
        imported++;
      } catch (err: any) {
        errors.push(`Failed "${item.legalName}": ${err.message}`);
      }
    }

    return { imported, errors };
  }

  async importPriceListFromExcel(customerId: string, fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    await this.findOne(customerId);

    // Fetch zones and vehicle types for lookup
    const [zones, vehicleTypes] = await Promise.all([
      this.prisma.zone.findMany({ select: { id: true, name: true } }),
      this.prisma.vehicleType.findMany({ where: { isActive: true }, select: { id: true, name: true } }),
    ]);

    const zoneMap = new Map(zones.map((z) => [z.name.toLowerCase(), z.id]));
    const vehicleTypeMap = new Map(vehicleTypes.map((vt) => [vt.name.toLowerCase(), vt.id]));

    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const priceSheet = workbook.getWorksheet('Price List');
    if (!priceSheet) {
      throw new BadRequestException('Invalid template: "Price List" sheet not found');
    }

    const items: PriceItemDto[] = [];
    const errors: string[] = [];

    priceSheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return; // Skip header

      const serviceType = String(row.getCell(1).value || '').trim().toUpperCase();
      const fromZoneName = String(row.getCell(2).value || '').trim();
      const toZoneName = String(row.getCell(3).value || '').trim();
      const vehicleTypeName = String(row.getCell(4).value || '').trim();
      const transferPrice = Number(row.getCell(5).value) || 0;
      const driverTip = Number(row.getCell(6).value) || 0;

      if (!serviceType && !fromZoneName && !toZoneName && !vehicleTypeName) {
        return; // Empty row
      }

      if (!serviceType || !fromZoneName || !toZoneName || !vehicleTypeName) {
        errors.push(`Row ${rowNumber}: Missing required fields`);
        return;
      }

      if (!VALID_SERVICE_TYPES.has(serviceType)) {
        errors.push(`Row ${rowNumber}: Unknown service type "${serviceType}"`);
        return;
      }

      const fromZoneId = zoneMap.get(fromZoneName.toLowerCase());
      const toZoneId = zoneMap.get(toZoneName.toLowerCase());
      const vehicleTypeId = vehicleTypeMap.get(vehicleTypeName.toLowerCase());

      if (!fromZoneId) {
        errors.push(`Row ${rowNumber}: Unknown zone "${fromZoneName}"`);
        return;
      }
      if (!toZoneId) {
        errors.push(`Row ${rowNumber}: Unknown zone "${toZoneName}"`);
        return;
      }
      if (!vehicleTypeId) {
        errors.push(`Row ${rowNumber}: Unknown vehicle type "${vehicleTypeName}"`);
        return;
      }

      if (transferPrice > 0 || driverTip > 0) {
        items.push({
          serviceType,
          fromZoneId,
          toZoneId,
          vehicleTypeId,
          transferPrice,
          driverTip,
        });
      }
    });

    if (items.length > 0) {
      await this.upsertPriceItems(customerId, { items });
    }

    return { imported: items.length, errors };
  }
}
