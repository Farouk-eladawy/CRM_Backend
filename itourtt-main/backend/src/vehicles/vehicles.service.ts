import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { Currency } from '../../generated/prisma/enums.js';
import ExcelJS from 'exceljs';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateVehicleTypeDto } from './dto/create-vehicle-type.dto.js';
import { CreateVehicleDto } from './dto/create-vehicle.dto.js';
import { UpsertVehicleComplianceDto } from './dto/upsert-vehicle-compliance.dto.js';
import { CreateDepositPaymentDto } from './dto/create-deposit-payment.dto.js';

@Injectable()
export class VehiclesService {
  constructor(private readonly prisma: PrismaService) {}

  // ─── Vehicle Types ────────────────────────────────────────

  async findAllVehicleTypes() {
    return this.prisma.vehicleType.findMany({
      orderBy: { name: 'asc' },
    });
  }

  async createVehicleType(dto: CreateVehicleTypeDto) {
    return this.prisma.vehicleType.create({
      data: {
        name: dto.name,
        seatCapacity: dto.seatCapacity,
        imageUrl: dto.imageUrl ?? null,
        description: dto.description ?? null,
        wifi: dto.wifi ?? false,
        airConditioning: dto.airConditioning ?? false,
        gpsTracked: dto.gpsTracked ?? false,
        luggageCapacity: dto.luggageCapacity ?? null,
        transmission: dto.transmission ?? null,
      },
    });
  }

  async updateVehicleType(id: string, dto: CreateVehicleTypeDto) {
    const existing = await this.prisma.vehicleType.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException('Vehicle type not found');
    return this.prisma.vehicleType.update({
      where: { id },
      data: {
        name: dto.name,
        seatCapacity: dto.seatCapacity,
        ...(dto.imageUrl !== undefined && { imageUrl: dto.imageUrl || null }),
        ...(dto.description !== undefined && { description: dto.description || null }),
        ...(dto.wifi !== undefined && { wifi: dto.wifi }),
        ...(dto.airConditioning !== undefined && { airConditioning: dto.airConditioning }),
        ...(dto.gpsTracked !== undefined && { gpsTracked: dto.gpsTracked }),
        ...(dto.luggageCapacity !== undefined && { luggageCapacity: dto.luggageCapacity ?? null }),
        ...(dto.transmission !== undefined && { transmission: dto.transmission ?? null }),
      },
    });
  }

  // ─── Vehicles ─────────────────────────────────────────────

  async findAllVehicles(page: number, limit: number, vehicleTypeId?: string, ownership?: string) {
    const skip = (page - 1) * limit;

    const where: Record<string, unknown> = { deletedAt: null, isActive: true };
    if (vehicleTypeId) {
      where.vehicleTypeId = vehicleTypeId;
    }
    if (ownership) {
      where.ownership = ownership;
    }

    const [data, total] = await Promise.all([
      this.prisma.vehicle.findMany({
        where,
        orderBy: { plateNumber: 'asc' },
        skip,
        take: limit,
        include: { vehicleType: true, compliance: true },
      }),
      this.prisma.vehicle.count({ where }),
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

  async findVehicleById(id: string) {
    const vehicle = await this.prisma.vehicle.findUnique({
      where: { id, deletedAt: null },
      include: { vehicleType: true, compliance: true },
    });

    if (!vehicle) {
      throw new NotFoundException(`Vehicle with id ${id} not found`);
    }

    return vehicle;
  }

  async createVehicle(dto: CreateVehicleDto) {
    const vehicleType = await this.prisma.vehicleType.findUnique({
      where: { id: dto.vehicleTypeId },
    });
    if (!vehicleType) {
      throw new NotFoundException(`VehicleType with id ${dto.vehicleTypeId} not found`);
    }

    return this.prisma.vehicle.create({
      data: {
        plateNumber: dto.plateNumber,
        vehicleTypeId: dto.vehicleTypeId,
        ownership: dto.ownership,
        color: dto.color,
        carBrand: dto.carBrand,
        carModel: dto.carModel,
        makeYear: dto.makeYear,
        luggageCapacity: dto.luggageCapacity,
        supplierId: dto.supplierId || null,
      },
      include: { vehicleType: true },
    });
  }

  async toggleStatus(id: string) {
    const vehicle = await this.prisma.vehicle.findUnique({
      where: { id, deletedAt: null },
    });
    if (!vehicle) {
      throw new NotFoundException(`Vehicle with id ${id} not found`);
    }

    return this.prisma.vehicle.update({
      where: { id },
      data: { isActive: !vehicle.isActive },
    });
  }

  async softDelete(id: string) {
    const vehicle = await this.prisma.vehicle.findUnique({
      where: { id, deletedAt: null },
    });
    if (!vehicle) {
      throw new NotFoundException(`Vehicle with id ${id} not found`);
    }

    return this.prisma.vehicle.update({
      where: { id },
      data: { deletedAt: new Date(), isActive: false },
    });
  }

  async updateVehicle(id: string, dto: Partial<CreateVehicleDto>) {
    const vehicle = await this.prisma.vehicle.findUnique({
      where: { id, deletedAt: null },
    });
    if (!vehicle) {
      throw new NotFoundException(`Vehicle with id ${id} not found`);
    }

    if (dto.vehicleTypeId) {
      const vehicleType = await this.prisma.vehicleType.findUnique({
        where: { id: dto.vehicleTypeId },
      });
      if (!vehicleType) {
        throw new NotFoundException(`VehicleType with id ${dto.vehicleTypeId} not found`);
      }
    }

    return this.prisma.vehicle.update({
      where: { id },
      data: {
        ...(dto.plateNumber !== undefined && { plateNumber: dto.plateNumber }),
        ...(dto.vehicleTypeId !== undefined && { vehicleTypeId: dto.vehicleTypeId }),
        ...(dto.ownership !== undefined && { ownership: dto.ownership }),
        ...(dto.color !== undefined && { color: dto.color }),
        ...(dto.carBrand !== undefined && { carBrand: dto.carBrand }),
        ...(dto.carModel !== undefined && { carModel: dto.carModel }),
        ...(dto.makeYear !== undefined && { makeYear: dto.makeYear }),
        ...(dto.luggageCapacity !== undefined && { luggageCapacity: dto.luggageCapacity }),
        ...(dto.supplierId !== undefined && { supplierId: dto.supplierId || null }),
      },
      include: { vehicleType: true },
    });
  }

  // ─── Export to Excel ──────────────────────────────────────

  async exportToExcel(): Promise<Buffer> {
    const vehicles = await this.prisma.vehicle.findMany({
      where: { deletedAt: null },
      orderBy: { plateNumber: 'asc' },
      include: { vehicleType: true, compliance: true },
    });

    const formatDate = (d: Date | null | undefined) => d ? new Date(d).toISOString().split('T')[0] : '';

    const rows = vehicles.map((v) => {
      const c = v.compliance;
      return {
        'Plate Number': v.plateNumber,
        'Vehicle Type': v.vehicleType?.name || '',
        Ownership: v.ownership || '',
        Color: v.color || '',
        'Car Brand': v.carBrand || '',
        'Car Model': v.carModel || '',
        'Make Year': v.makeYear ?? '',
        'Luggage Capacity': v.luggageCapacity ?? '',
        Status: v.isActive ? 'Active' : 'Inactive',
        'License Expiry Date': formatDate(c?.licenseExpiryDate),
        'Has Insurance': c?.hasInsurance ? 'YES' : 'NO',
        'Insurance Expiry Date': formatDate(c?.insuranceExpiryDate),
        'Annual Fees': c?.annualPayment != null ? Number(c.annualPayment) : '',
        'Annual Fees Currency': c?.annualPaymentCurrency || '',
        'GPS Subscription': c?.gpsSubscription != null ? Number(c.gpsSubscription) : '',
        'GPS Currency': c?.gpsSubscriptionCurrency || '',
        'Tourism Support Fund': c?.tourismSupportFund != null ? Number(c.tourismSupportFund) : '',
        'Tourism Fund Currency': c?.tourismSupportFundCurrency || '',
        'Registration Fees': c?.registrationFees != null ? Number(c.registrationFees) : '',
        'Registration Fees Currency': c?.registrationFeesCurrency || '',
        'Temporary Permit Date': formatDate(c?.temporaryPermitDate),
      };
    });

    const ws = XLSX.utils.json_to_sheet(rows);

    const colWidths = Object.keys(rows[0] || {}).map((key) => {
      const maxLen = Math.max(
        key.length,
        ...rows.map((r) => String((r as any)[key] || '').length),
      );
      return { wch: Math.min(maxLen + 2, 40) };
    });
    ws['!cols'] = colWidths;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Vehicles');
    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ─── Import Template ──────────────────────────────────────

  async generateImportTemplate(): Promise<Buffer> {
    const vehicleTypes = await this.prisma.vehicleType.findMany({
      orderBy: { name: 'asc' },
    });

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    // Instructions sheet
    const instructionsSheet = workbook.addWorksheet('Instructions');
    instructionsSheet.columns = [{ width: 80 }];
    instructionsSheet.addRow(['Vehicle Bulk Import Template']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Instructions:']);
    instructionsSheet.addRow(['1. Fill in vehicle data in the "Vehicles" sheet']);
    instructionsSheet.addRow(['2. Plate Number and Vehicle Type are required fields']);
    instructionsSheet.addRow(['3. Vehicle Type must match one of the existing types exactly (see list below)']);
    instructionsSheet.addRow(['4. Ownership must be one of: OWNED, RENTED, CONTRACTED (defaults to OWNED)']);
    instructionsSheet.addRow(['5. Car Brand, Car Model, Make Year, and Luggage Capacity are optional']);
    instructionsSheet.addRow(['6. Compliance fields (columns I-T) are optional']);
    instructionsSheet.addRow(['7. Has Insurance must be YES or NO (defaults to NO)']);
    instructionsSheet.addRow(['8. Currency must be one of: EGP, USD, EUR, GBP, SAR (defaults to EGP)']);
    instructionsSheet.addRow(['9. Date fields must be in YYYY-MM-DD format']);
    instructionsSheet.addRow(['10. Do not modify column headers']);
    instructionsSheet.addRow(['11. Save the file and upload it via the import button']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Notes:']);
    instructionsSheet.addRow(['- Duplicate plate numbers will be skipped with an error']);
    instructionsSheet.addRow(['- Maximum 500 vehicles per import']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Available Vehicle Types:']);
    for (const vt of vehicleTypes) {
      instructionsSheet.addRow([`  - ${vt.name} (${vt.seatCapacity} seats)`]);
    }
    instructionsSheet.getRow(1).font = { bold: true, size: 14 };
    instructionsSheet.getRow(3).font = { bold: true };
    instructionsSheet.getRow(15).font = { bold: true };
    instructionsSheet.getRow(19).font = { bold: true };

    // Vehicles data sheet
    const vehiclesSheet = workbook.addWorksheet('Vehicles');
    vehiclesSheet.columns = [
      { header: 'Plate Number', key: 'plateNumber', width: 20 },
      { header: 'Vehicle Type', key: 'vehicleType', width: 20 },
      { header: 'Ownership', key: 'ownership', width: 15 },
      { header: 'Color', key: 'color', width: 15 },
      { header: 'Car Brand', key: 'carBrand', width: 20 },
      { header: 'Car Model', key: 'carModel', width: 20 },
      { header: 'Make Year', key: 'makeYear', width: 12 },
      { header: 'Luggage Capacity', key: 'luggageCapacity', width: 18 },
      { header: 'License Expiry Date', key: 'licenseExpiryDate', width: 20 },
      { header: 'Has Insurance', key: 'hasInsurance', width: 15 },
      { header: 'Insurance Expiry Date', key: 'insuranceExpiryDate', width: 22 },
      { header: 'Annual Fees', key: 'annualPayment', width: 16 },
      { header: 'Annual Fees Currency', key: 'annualPaymentCurrency', width: 24 },
      { header: 'GPS Subscription', key: 'gpsSubscription', width: 18 },
      { header: 'GPS Currency', key: 'gpsSubscriptionCurrency', width: 15 },
      { header: 'Tourism Support Fund', key: 'tourismSupportFund', width: 22 },
      { header: 'Tourism Fund Currency', key: 'tourismSupportFundCurrency', width: 22 },
      { header: 'Registration Fees', key: 'registrationFees', width: 18 },
      { header: 'Registration Fees Currency', key: 'registrationFeesCurrency', width: 26 },
      { header: 'Temporary Permit Date', key: 'temporaryPermitDate', width: 22 },
    ];

    // Style header row
    const headerRow = vehiclesSheet.getRow(1);
    headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF4472C4' },
    };
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' };

    // Add sample rows
    const sampleType = vehicleTypes[0]?.name || 'Sedan';
    vehiclesSheet.addRow({
      plateNumber: 'ABC-1234',
      vehicleType: sampleType,
      ownership: 'OWNED',
      color: 'White',
      carBrand: 'Toyota',
      carModel: 'Hiace',
      makeYear: 2023,
      luggageCapacity: 6,
      licenseExpiryDate: '2025-12-31',
      hasInsurance: 'YES',
      insuranceExpiryDate: '2025-06-30',
      annualPayment: '',
      annualPaymentCurrency: '',
      gpsSubscription: 150,
      gpsSubscriptionCurrency: 'EGP',
      tourismSupportFund: 500,
      tourismSupportFundCurrency: 'EGP',
      registrationFees: '',
      registrationFeesCurrency: '',
      temporaryPermitDate: '2025-01-15',
    });
    vehiclesSheet.addRow({
      plateNumber: 'XYZ-5678',
      vehicleType: sampleType,
      ownership: 'CONTRACTED',
      color: 'Black',
      carBrand: 'Mercedes',
      carModel: 'Sprinter',
      makeYear: 2022,
      luggageCapacity: 8,
      licenseExpiryDate: '2026-03-15',
      hasInsurance: 'YES',
      insuranceExpiryDate: '2026-01-01',
      annualPayment: 50000,
      annualPaymentCurrency: 'EGP',
      gpsSubscription: 200,
      gpsSubscriptionCurrency: 'EGP',
      tourismSupportFund: 1000,
      tourismSupportFundCurrency: 'EGP',
      registrationFees: 5000,
      registrationFeesCurrency: 'EGP',
      temporaryPermitDate: '2025-06-01',
    });

    // Style sample rows in italic gray
    for (let i = 2; i <= 3; i++) {
      const row = vehiclesSheet.getRow(i);
      row.font = { italic: true, color: { argb: 'FF999999' } };
    }

    // Add data validation for Ownership column (C)
    for (let i = 2; i <= 1000; i++) {
      (vehiclesSheet.getCell(`C${i}`) as any).dataValidation = {
        type: 'list',
        allowBlank: true,
        formulae: ['"OWNED,RENTED,CONTRACTED"'],
      };
    }

    // Add data validation for Color column (D)
    const colorOptions = 'White,Black,Silver,Gray,Red,Blue,Green,Yellow,Orange,Brown,Beige,Gold,Maroon,Navy,Burgundy';
    for (let i = 2; i <= 1000; i++) {
      (vehiclesSheet.getCell(`D${i}`) as any).dataValidation = {
        type: 'list',
        allowBlank: true,
        formulae: [`"${colorOptions}"`],
      };
    }

    // Add data validation for Vehicle Type column (B)
    if (vehicleTypes.length > 0) {
      const typeNames = vehicleTypes.map((vt) => vt.name).join(',');
      for (let i = 2; i <= 1000; i++) {
        (vehiclesSheet.getCell(`B${i}`) as any).dataValidation = {
          type: 'list',
          allowBlank: false,
          formulae: [`"${typeNames}"`],
        };
      }
    }

    // Add data validation for Has Insurance column (J)
    for (let i = 2; i <= 1000; i++) {
      (vehiclesSheet.getCell(`J${i}`) as any).dataValidation = {
        type: 'list',
        allowBlank: true,
        formulae: ['"YES,NO"'],
      };
    }

    // Add data validation for currency columns (M, O, Q, T)
    const currencyOptions = '"EGP,USD,EUR,GBP,SAR"';
    const currencyCols = ['M', 'O', 'Q', 'S'];
    for (const col of currencyCols) {
      for (let i = 2; i <= 1000; i++) {
        (vehiclesSheet.getCell(`${col}${i}`) as any).dataValidation = {
          type: 'list',
          allowBlank: true,
          formulae: [currencyOptions],
        };
      }
    }

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  // ─── Bulk Import ──────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer, supplierId?: string): Promise<{ imported: number; updated: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const vehiclesSheet = workbook.getWorksheet('Vehicles');
    if (!vehiclesSheet) {
      throw new BadRequestException('Invalid template: "Vehicles" sheet not found');
    }

    // Pre-load vehicle types for name → id lookup
    const vehicleTypes = await this.prisma.vehicleType.findMany();
    const typeNameMap = new Map(vehicleTypes.map((vt) => [vt.name.toLowerCase(), vt.id]));

    const validCurrencies = ['EGP', 'USD', 'EUR', 'GBP', 'SAR'];

    interface ImportItem {
      plateNumber: string;
      vehicleTypeId: string;
      ownership?: 'OWNED' | 'RENTED' | 'CONTRACTED';
      color?: string;
      carBrand?: string;
      carModel?: string;
      makeYear?: number;
      luggageCapacity?: number;
      compliance?: {
        licenseExpiryDate?: Date;
        hasInsurance?: boolean;
        insuranceExpiryDate?: Date;
        annualPayment?: number;
        annualPaymentCurrency?: Currency;
        gpsSubscription?: number;
        gpsSubscriptionCurrency?: Currency;
        tourismSupportFund?: number;
        tourismSupportFundCurrency?: Currency;
        registrationFees?: number;
        registrationFeesCurrency?: Currency;
        temporaryPermitDate?: Date;
      };
    }

    const items: ImportItem[] = [];
    const errors: string[] = [];

    vehiclesSheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return; // Skip header

      const plateNumber = String(row.getCell(1).value || '').trim();
      const vehicleTypeName = String(row.getCell(2).value || '').trim();
      const ownershipRaw = String(row.getCell(3).value || '').trim().toUpperCase();
      const color = String(row.getCell(4).value || '').trim();
      const carBrand = String(row.getCell(5).value || '').trim();
      const carModel = String(row.getCell(6).value || '').trim();
      const makeYearRaw = row.getCell(7).value;
      const luggageCapRaw = row.getCell(8).value;

      // Compliance columns (9-20)
      const licenseExpiryRaw = String(row.getCell(9).value || '').trim();
      const hasInsuranceRaw = String(row.getCell(10).value || '').trim().toUpperCase();
      const insuranceExpiryRaw = String(row.getCell(11).value || '').trim();
      const annualPaymentRaw = row.getCell(12).value;
      const annualPaymentCurrRaw = String(row.getCell(13).value || '').trim().toUpperCase();
      const gpsSubRaw = row.getCell(14).value;
      const gpsSubCurrRaw = String(row.getCell(15).value || '').trim().toUpperCase();
      const tourismFundRaw = row.getCell(16).value;
      const tourismFundCurrRaw = String(row.getCell(17).value || '').trim().toUpperCase();
      const registrationFeesRaw = row.getCell(18).value;
      const registrationFeesCurrRaw = String(row.getCell(19).value || '').trim().toUpperCase();
      const tempPermitRaw = String(row.getCell(20).value || '').trim();

      // Skip empty rows
      if (!plateNumber && !vehicleTypeName) return;

      // Skip sample rows
      if (plateNumber === 'ABC-1234' || plateNumber === 'XYZ-5678') return;

      // Validate required fields
      if (!plateNumber) {
        errors.push(`Row ${rowNumber}: Plate Number is required`);
        return;
      }
      if (!vehicleTypeName) {
        errors.push(`Row ${rowNumber}: Vehicle Type is required`);
        return;
      }

      // Resolve vehicle type
      const vehicleTypeId = typeNameMap.get(vehicleTypeName.toLowerCase());
      if (!vehicleTypeId) {
        errors.push(`Row ${rowNumber}: Vehicle Type "${vehicleTypeName}" not found`);
        return;
      }

      // Validate ownership
      let ownership: 'OWNED' | 'RENTED' | 'CONTRACTED' | undefined;
      if (ownershipRaw && ['OWNED', 'RENTED', 'CONTRACTED'].includes(ownershipRaw)) {
        ownership = ownershipRaw as 'OWNED' | 'RENTED' | 'CONTRACTED';
      } else if (ownershipRaw && ownershipRaw.length > 0) {
        errors.push(`Row ${rowNumber}: Invalid ownership "${ownershipRaw}" (must be OWNED, RENTED, or CONTRACTED)`);
        return;
      }

      // Parse make year
      let makeYear: number | undefined;
      if (makeYearRaw !== null && makeYearRaw !== undefined && String(makeYearRaw).trim() !== '') {
        const parsed = parseInt(String(makeYearRaw), 10);
        if (isNaN(parsed) || parsed < 1900 || parsed > 2100) {
          errors.push(`Row ${rowNumber}: Invalid make year "${makeYearRaw}" (must be 1900-2100)`);
          return;
        }
        makeYear = parsed;
      }

      // Parse luggage capacity
      let luggageCapacity: number | undefined;
      if (luggageCapRaw !== null && luggageCapRaw !== undefined && String(luggageCapRaw).trim() !== '') {
        const parsed = parseInt(String(luggageCapRaw), 10);
        if (isNaN(parsed) || parsed < 0) {
          errors.push(`Row ${rowNumber}: Invalid luggage capacity "${luggageCapRaw}"`);
          return;
        }
        luggageCapacity = parsed;
      }

      // Parse compliance fields
      const compliance: ImportItem['compliance'] = {};
      let hasCompliance = false;

      // License expiry date
      if (licenseExpiryRaw) {
        const d = new Date(licenseExpiryRaw);
        if (isNaN(d.getTime())) {
          errors.push(`Row ${rowNumber}: Invalid License Expiry Date "${licenseExpiryRaw}"`);
          return;
        }
        compliance.licenseExpiryDate = d;
        hasCompliance = true;
      }

      // Has Insurance
      if (hasInsuranceRaw === 'YES') {
        compliance.hasInsurance = true;
        hasCompliance = true;
      } else if (hasInsuranceRaw === 'NO' || !hasInsuranceRaw) {
        compliance.hasInsurance = false;
      } else {
        errors.push(`Row ${rowNumber}: Has Insurance must be YES or NO`);
        return;
      }

      // Insurance expiry date
      if (insuranceExpiryRaw) {
        const d = new Date(insuranceExpiryRaw);
        if (isNaN(d.getTime())) {
          errors.push(`Row ${rowNumber}: Invalid Insurance Expiry Date "${insuranceExpiryRaw}"`);
          return;
        }
        compliance.insuranceExpiryDate = d;
        hasCompliance = true;
      }

      // Helper to parse a decimal column
      const parseDecimal = (raw: unknown, label: string): number | undefined => {
        if (raw === null || raw === undefined || String(raw).trim() === '') return undefined;
        const parsed = parseFloat(String(raw));
        if (isNaN(parsed) || parsed < 0) {
          errors.push(`Row ${rowNumber}: Invalid ${label} "${raw}"`);
          return undefined;
        }
        return parsed;
      };

      // Helper to validate currency
      const parseCurrency = (raw: string): Currency | undefined => {
        if (!raw) return undefined;
        if (!validCurrencies.includes(raw)) return undefined;
        return raw as Currency;
      };

      const annualPayment = parseDecimal(annualPaymentRaw, 'Annual Fees');
      if (annualPayment !== undefined) {
        compliance.annualPayment = annualPayment;
        compliance.annualPaymentCurrency = parseCurrency(annualPaymentCurrRaw) || Currency.EGP;
        hasCompliance = true;
      }

      const gpsSub = parseDecimal(gpsSubRaw, 'GPS Subscription');
      if (gpsSub !== undefined) {
        compliance.gpsSubscription = gpsSub;
        compliance.gpsSubscriptionCurrency = parseCurrency(gpsSubCurrRaw) || Currency.EGP;
        hasCompliance = true;
      }

      const tourismFund = parseDecimal(tourismFundRaw, 'Tourism Support Fund');
      if (tourismFund !== undefined) {
        compliance.tourismSupportFund = tourismFund;
        compliance.tourismSupportFundCurrency = parseCurrency(tourismFundCurrRaw) || Currency.EGP;
        hasCompliance = true;
      }

      const regFees = parseDecimal(registrationFeesRaw, 'Registration Fees');
      if (regFees !== undefined) {
        compliance.registrationFees = regFees;
        compliance.registrationFeesCurrency = parseCurrency(registrationFeesCurrRaw) || Currency.EGP;
        hasCompliance = true;
      }

      // Temporary permit date
      if (tempPermitRaw) {
        const d = new Date(tempPermitRaw);
        if (isNaN(d.getTime())) {
          errors.push(`Row ${rowNumber}: Invalid Temporary Permit Date "${tempPermitRaw}"`);
          return;
        }
        compliance.temporaryPermitDate = d;
        hasCompliance = true;
      }

      items.push({
        plateNumber,
        vehicleTypeId,
        ...(ownership && { ownership }),
        ...(color && { color }),
        ...(carBrand && { carBrand }),
        ...(carModel && { carModel }),
        ...(makeYear !== undefined && { makeYear }),
        ...(luggageCapacity !== undefined && { luggageCapacity }),
        ...(hasCompliance && { compliance }),
      });
    });

    if (items.length === 0 && errors.length === 0) {
      throw new BadRequestException('No data found in the Vehicles sheet');
    }

    if (items.length > 500) {
      throw new BadRequestException('Maximum 500 vehicles per import. Please split into multiple files.');
    }

    // Check for duplicates within the import batch
    const platesSeen = new Set<string>();
    const deduped: typeof items = [];
    for (const item of items) {
      const key = item.plateNumber.toLowerCase();
      if (platesSeen.has(key)) {
        errors.push(`Duplicate plate "${item.plateNumber}" in import file — skipped`);
        continue;
      }
      platesSeen.add(key);
      deduped.push(item);
    }

    // Check for existing plate numbers in database
    const existingVehicles = await this.prisma.vehicle.findMany({
      where: {
        plateNumber: { in: deduped.map((v) => v.plateNumber) },
        deletedAt: null,
      },
      select: { id: true, plateNumber: true },
    });

    const existingPlateMap = new Map(
      existingVehicles.map((v) => [v.plateNumber.toLowerCase(), v.id]),
    );
    const toCreate: typeof deduped = [];
    const toUpdate: { id: string; item: (typeof deduped)[0] }[] = [];

    for (const item of deduped) {
      const existingId = existingPlateMap.get(item.plateNumber.toLowerCase());
      if (existingId) {
        toUpdate.push({ id: existingId, item });
      } else {
        toCreate.push(item);
      }
    }

    // Bulk create + update in a transaction
    let updated = 0;
    if (toCreate.length > 0 || toUpdate.length > 0) {
      await this.prisma.$transaction(async (tx) => {
        for (const v of toCreate) {
          const created = await tx.vehicle.create({
            data: {
              plateNumber: v.plateNumber,
              vehicleTypeId: v.vehicleTypeId,
              ownership: v.ownership,
              color: v.color,
              carBrand: v.carBrand,
              carModel: v.carModel,
              makeYear: v.makeYear,
              luggageCapacity: v.luggageCapacity,
              supplierId: supplierId || null,
            },
          });

          if (v.compliance) {
            await tx.vehicleCompliance.create({
              data: {
                vehicleId: created.id,
                ...v.compliance,
              },
            });
          }
        }

        // Update existing vehicles (assign supplier + update fields)
        for (const { id, item } of toUpdate) {
          await tx.vehicle.update({
            where: { id },
            data: {
              vehicleTypeId: item.vehicleTypeId,
              ...(item.ownership && { ownership: item.ownership }),
              ...(item.color && { color: item.color }),
              ...(item.carBrand && { carBrand: item.carBrand }),
              ...(item.carModel && { carModel: item.carModel }),
              ...(item.makeYear !== undefined && { makeYear: item.makeYear }),
              ...(item.luggageCapacity !== undefined && { luggageCapacity: item.luggageCapacity }),
              ...(supplierId !== undefined && { supplierId: supplierId || null }),
            },
          });
          updated++;
        }
      });
    }

    return { imported: toCreate.length, updated, errors };
  }

  // ─── Vehicle Compliance ─────────────────────────────────

  async getCompliance(vehicleId: string) {
    await this.findVehicleById(vehicleId);
    return this.prisma.vehicleCompliance.findUnique({
      where: { vehicleId },
      include: { depositPayments: { orderBy: { paidAt: 'desc' } } },
    });
  }

  async upsertCompliance(vehicleId: string, dto: UpsertVehicleComplianceDto) {
    await this.findVehicleById(vehicleId);

    const data: Record<string, unknown> = {};
    if (dto.licenseExpiryDate !== undefined) data.licenseExpiryDate = new Date(dto.licenseExpiryDate);
    if (dto.hasInsurance !== undefined) data.hasInsurance = dto.hasInsurance;
    if (dto.insuranceExpiryDate !== undefined) data.insuranceExpiryDate = new Date(dto.insuranceExpiryDate);
    if (dto.annualPayment !== undefined) data.annualPayment = dto.annualPayment;
    if (dto.annualPaymentCurrency !== undefined) data.annualPaymentCurrency = dto.annualPaymentCurrency;
    if (dto.gpsSubscription !== undefined) data.gpsSubscription = dto.gpsSubscription;
    if (dto.gpsSubscriptionCurrency !== undefined) data.gpsSubscriptionCurrency = dto.gpsSubscriptionCurrency;
    if (dto.tourismSupportFund !== undefined) data.tourismSupportFund = dto.tourismSupportFund;
    if (dto.tourismSupportFundCurrency !== undefined) data.tourismSupportFundCurrency = dto.tourismSupportFundCurrency;
    if (dto.registrationFees !== undefined) data.registrationFees = dto.registrationFees;
    if (dto.registrationFeesCurrency !== undefined) data.registrationFeesCurrency = dto.registrationFeesCurrency;
    if (dto.temporaryPermitDate !== undefined) data.temporaryPermitDate = new Date(dto.temporaryPermitDate);

    return this.prisma.vehicleCompliance.upsert({
      where: { vehicleId },
      create: { vehicleId, ...data },
      update: data,
    });
  }

  async updateComplianceFile(
    vehicleId: string,
    field: 'licenseCopyUrl' | 'insuranceDocUrl',
    url: string,
  ) {
    await this.findVehicleById(vehicleId);
    return this.prisma.vehicleCompliance.upsert({
      where: { vehicleId },
      create: { vehicleId, [field]: url },
      update: { [field]: url },
    });
  }

  async getComplianceReport() {
    const vehicles = await this.prisma.vehicle.findMany({
      where: { deletedAt: null },
      include: {
        vehicleType: true,
        compliance: { include: { depositPayments: true } },
      },
      orderBy: { plateNumber: 'asc' },
    });

    return vehicles.map((v) => {
      const c = v.compliance;
      const permitExpiry = c?.temporaryPermitDate
        ? new Date(new Date(c.temporaryPermitDate).setMonth(new Date(c.temporaryPermitDate).getMonth() + 3))
        : null;
      const annual = c?.annualPayment ? Number(c.annualPayment) : 0;
      const gps = c?.gpsSubscription ? Number(c.gpsSubscription) : 0;
      const tourism = c?.tourismSupportFund ? Number(c.tourismSupportFund) : 0;
      const registration = c?.registrationFees ? Number(c.registrationFees) : 0;
      const totalFees = annual + gps + tourism + registration;
      const depositTotal = (c?.depositPayments || []).reduce(
        (sum, d) => sum + Number(d.amount), 0,
      );

      return {
        id: v.id,
        plateNumber: v.plateNumber,
        vehicleTypeName: v.vehicleType?.name,
        ownership: v.ownership,
        isActive: v.isActive,
        licenseExpiryDate: c?.licenseExpiryDate,
        hasInsurance: c?.hasInsurance ?? false,
        insuranceExpiryDate: c?.insuranceExpiryDate,
        gpsSubscription: c?.gpsSubscription ? Number(c.gpsSubscription) : null,
        gpsSubscriptionCurrency: c?.gpsSubscriptionCurrency,
        tourismSupportFund: c?.tourismSupportFund ? Number(c.tourismSupportFund) : null,
        tourismSupportFundCurrency: c?.tourismSupportFundCurrency,
        registrationFees: c?.registrationFees ? Number(c.registrationFees) : null,
        registrationFeesCurrency: c?.registrationFeesCurrency,
        temporaryPermitDate: c?.temporaryPermitDate,
        temporaryPermitExpiryDate: permitExpiry,
        annualPayment: annual || null,
        annualPaymentCurrency: c?.annualPaymentCurrency,
        totalFees: v.ownership === 'CONTRACTED' ? totalFees : null,
        depositTotal: depositTotal > 0 ? depositTotal : null,
        balanceRemaining: v.ownership === 'CONTRACTED' ? totalFees - depositTotal : null,
      };
    });
  }

  // ─── Deposit Payments ─────────────────────────────────

  async addDepositPayment(vehicleId: string, dto: CreateDepositPaymentDto, userId: string) {
    await this.findVehicleById(vehicleId);

    // Ensure compliance record exists
    const compliance = await this.prisma.vehicleCompliance.upsert({
      where: { vehicleId },
      create: { vehicleId },
      update: {},
    });

    // Look up user name for the audit log
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: { name: true },
    });

    return this.prisma.vehicleDepositPayment.create({
      data: {
        complianceId: compliance.id,
        amount: dto.amount,
        currency: dto.currency as Currency,
        paidAt: new Date(dto.paidAt),
        createdByName: user?.name || 'Unknown',
      },
    });
  }

  async removeDepositPayment(vehicleId: string, depositId: string) {
    await this.findVehicleById(vehicleId);

    const deposit = await this.prisma.vehicleDepositPayment.findUnique({
      where: { id: depositId },
      include: { compliance: true },
    });

    if (!deposit || deposit.compliance.vehicleId !== vehicleId) {
      throw new NotFoundException(`Deposit payment not found for vehicle ${vehicleId}`);
    }

    return this.prisma.vehicleDepositPayment.delete({
      where: { id: depositId },
    });
  }

  async listDepositPayments(vehicleId: string) {
    await this.findVehicleById(vehicleId);
    const compliance = await this.prisma.vehicleCompliance.findUnique({
      where: { vehicleId },
    });
    if (!compliance) return [];

    return this.prisma.vehicleDepositPayment.findMany({
      where: { complianceId: compliance.id },
      orderBy: { paidAt: 'desc' },
    });
  }
}
