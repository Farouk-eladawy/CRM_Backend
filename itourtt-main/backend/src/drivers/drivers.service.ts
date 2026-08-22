import { Injectable, NotFoundException, ConflictException, BadRequestException } from '@nestjs/common';
import * as bcrypt from 'bcryptjs';
import ExcelJS from 'exceljs';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateDriverDto } from './dto/create-driver.dto.js';
import { UpdateDriverDto } from './dto/update-driver.dto.js';
import { AssignVehicleDto } from './dto/assign-vehicle.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { PaginatedResponse } from '../common/dto/api-response.dto.js';

@Injectable()
export class DriversService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(pagination: PaginationDto, isActive?: boolean) {
    const { page = 1, limit = 20 } = pagination;
    const skip = (page - 1) * limit;

    const where: Record<string, unknown> = { deletedAt: null };
    if (isActive !== undefined) {
      where.isActive = isActive;
    }

    const [data, total] = await Promise.all([
      this.prisma.driver.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          user: { select: { id: true, email: true, name: true, role: true, isActive: true } },
          driverVehicles: {
            where: { unassignedAt: null },
            include: { vehicle: { include: { vehicleType: true } } },
          },
        },
      }),
      this.prisma.driver.count({ where }),
    ]);

    return new PaginatedResponse(data, total, page, limit);
  }

  async findOne(id: string) {
    const driver = await this.prisma.driver.findFirst({
      where: { id, deletedAt: null },
      include: {
        user: { select: { id: true, email: true, name: true, role: true, isActive: true } },
        driverVehicles: {
          where: { unassignedAt: null },
          include: { vehicle: { include: { vehicleType: true } } },
        },
      },
    });

    if (!driver) {
      throw new NotFoundException(`Driver with ID "${id}" not found`);
    }

    return driver;
  }

  async getTripFees(driverId: string, from?: string, to?: string) {
    const where: Record<string, unknown> = { driverId };
    if (from || to) {
      const dateFilter: Record<string, Date> = {};
      if (from) dateFilter.gte = new Date(from);
      if (to) {
        const toDate = new Date(to);
        toDate.setHours(23, 59, 59, 999);
        dateFilter.lte = toDate;
      }
      where.createdAt = dateFilter;
    }

    const fees = await this.prisma.driverTripFee.findMany({
      where,
      include: {
        trafficJob: {
          select: {
            id: true,
            internalRef: true,
            serviceType: true,
            jobDate: true,
          },
        },
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
        fromAirport: { select: { id: true, name: true, code: true } },
        toAirport: { select: { id: true, name: true, code: true } },
        vehicleType: { select: { id: true, name: true } },
      },
      orderBy: { createdAt: 'desc' },
    });

    const totalAmount = fees.reduce((sum, f) => sum + Number(f.amount), 0);
    return { fees, totalAmount, count: fees.length };
  }

  async create(dto: CreateDriverDto) {
    return this.prisma.driver.create({
      data: {
        name: dto.name,
        mobileNumber: dto.mobileNumber,
        licenseNumber: dto.licenseNumber,
        licenseExpiryDate: dto.licenseExpiryDate ? new Date(dto.licenseExpiryDate) : undefined,
      },
    });
  }

  async update(id: string, dto: UpdateDriverDto) {
    await this.findOne(id);

    return this.prisma.driver.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.mobileNumber !== undefined && { mobileNumber: dto.mobileNumber }),
        ...(dto.licenseNumber !== undefined && { licenseNumber: dto.licenseNumber }),
        ...(dto.licenseExpiryDate !== undefined && {
          licenseExpiryDate: dto.licenseExpiryDate ? new Date(dto.licenseExpiryDate) : null,
        }),
      },
    });
  }

  async updateAttachment(id: string, url: string) {
    await this.findOne(id);
    return this.prisma.driver.update({
      where: { id },
      data: { attachmentUrl: url },
    });
  }

  async assignVehicle(driverId: string, dto: AssignVehicleDto) {
    await this.findOne(driverId);

    // Verify vehicle exists
    const vehicle = await this.prisma.vehicle.findFirst({
      where: { id: dto.vehicleId, deletedAt: null },
    });
    if (!vehicle) {
      throw new NotFoundException(`Vehicle with ID "${dto.vehicleId}" not found`);
    }

    // Check if assignment already exists (active)
    const existing = await this.prisma.driverVehicle.findFirst({
      where: {
        driverId,
        vehicleId: dto.vehicleId,
        unassignedAt: null,
      },
    });
    if (existing) {
      throw new ConflictException('This vehicle is already assigned to this driver');
    }

    // If isPrimary requested, unset any existing primary for this driver
    if (dto.isPrimary) {
      await this.prisma.driverVehicle.updateMany({
        where: { driverId, isPrimary: true, unassignedAt: null },
        data: { isPrimary: false },
      });
    }

    return this.prisma.driverVehicle.create({
      data: {
        driverId,
        vehicleId: dto.vehicleId,
        isPrimary: dto.isPrimary ?? false,
      },
      include: {
        vehicle: { include: { vehicleType: true } },
      },
    });
  }

  async unassignVehicle(driverId: string, vehicleId: string) {
    const assignment = await this.prisma.driverVehicle.findFirst({
      where: {
        driverId,
        vehicleId,
        unassignedAt: null,
      },
    });

    if (!assignment) {
      throw new NotFoundException(
        `Active assignment for driver "${driverId}" and vehicle "${vehicleId}" not found`,
      );
    }

    return this.prisma.driverVehicle.update({
      where: { id: assignment.id },
      data: { unassignedAt: new Date() },
    });
  }

  async createUserAccount(driverId: string, dto: { password: string }) {
    const driver = await this.findOne(driverId);

    if (driver.userId) {
      throw new ConflictException('This driver already has a user account');
    }

    if (!driver.mobileNumber) {
      throw new BadRequestException('Driver must have a mobile number to create an account');
    }

    // Check if phone already taken
    const existingPhone = await this.prisma.user.findUnique({
      where: { phone: driver.mobileNumber },
    });
    if (existingPhone) {
      throw new ConflictException('A user with this mobile number already exists');
    }

    const passwordHash = await bcrypt.hash(dto.password, 12);
    const portalEmail = `driver.${driver.mobileNumber}@portal.itour.local`;

    return this.prisma.$transaction(async (tx) => {
      const user = await tx.user.create({
        data: {
          email: portalEmail,
          phone: driver.mobileNumber,
          passwordHash,
          name: driver.name,
          role: 'DRIVER',
        },
      });

      await tx.driver.update({
        where: { id: driverId },
        data: { userId: user.id },
      });

      return {
        userId: user.id,
        phone: user.phone,
        name: user.name,
        role: user.role,
      };
    });
  }

  async toggleStatus(id: string) {
    const driver = await this.findOne(id);
    const newStatus = !driver.isActive;

    return this.prisma.$transaction(async (tx) => {
      const updated = await tx.driver.update({
        where: { id },
        data: { isActive: newStatus },
      });

      if (driver.userId) {
        await tx.user.update({
          where: { id: driver.userId },
          data: { isActive: newStatus },
        });
      }

      return updated;
    });
  }

  async softDelete(id: string) {
    const driver = await this.findOne(id);

    // Deactivate linked user account if exists
    if (driver.userId) {
      await this.prisma.user.update({
        where: { id: driver.userId },
        data: { isActive: false, refreshToken: null },
      });
    }

    return this.prisma.driver.update({
      where: { id },
      data: { deletedAt: new Date(), isActive: false },
    });
  }

  async resetPassword(driverId: string, newPassword: string) {
    const driver = await this.findOne(driverId);

    if (!driver.userId) {
      throw new BadRequestException('This driver does not have a user account');
    }

    const passwordHash = await bcrypt.hash(newPassword, 12);

    await this.prisma.user.update({
      where: { id: driver.userId },
      data: {
        passwordHash,
        refreshToken: null,
        sessionId: null,
        sessionExpiresAt: null,
      },
    });

    return { success: true };
  }

  // ──────────────────────────────────────────────
  // EXPORT – all drivers to Excel
  // ──────────────────────────────────────────────

  async exportToExcel(): Promise<Buffer> {
    const drivers = await this.prisma.driver.findMany({
      where: { deletedAt: null },
      orderBy: { name: 'asc' },
      include: { supplier: { select: { legalName: true } } },
    });

    const rows = drivers.map((d) => ({
      Name: d.name,
      'Mobile Number': d.mobileNumber,
      'License Number': d.licenseNumber || '',
      'License Expiry Date': d.licenseExpiryDate
        ? new Date(d.licenseExpiryDate).toISOString().split('T')[0]
        : '',
      'Supplier': (d as any).supplier?.legalName || '',
      Status: d.isActive ? 'Active' : 'Inactive',
    }));

    const ws = XLSX.utils.json_to_sheet(rows);

    // Auto-size columns
    const colWidths = Object.keys(rows[0] || {}).map((key) => {
      const maxLen = Math.max(
        key.length,
        ...rows.map((r) => String((r as any)[key] || '').length),
      );
      return { wch: Math.min(maxLen + 2, 40) };
    });
    ws['!cols'] = colWidths;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Drivers');
    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ──────────────────────────────────────────────
  // IMPORT TEMPLATE – generate Excel template
  // ──────────────────────────────────────────────

  async generateImportTemplate(): Promise<Buffer> {
    const suppliers = await this.prisma.supplier.findMany({
      where: { deletedAt: null },
      orderBy: { legalName: 'asc' },
      select: { legalName: true },
    });

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    // Instructions sheet
    const instructionsSheet = workbook.addWorksheet('Instructions');
    instructionsSheet.columns = [{ width: 80 }];
    instructionsSheet.addRow(['Driver Bulk Import Template']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Instructions:']);
    instructionsSheet.addRow(['1. Fill in driver data in the "Drivers" sheet']);
    instructionsSheet.addRow(['2. Name and Mobile Number are required fields']);
    instructionsSheet.addRow(['3. License Number and Supplier are optional']);
    instructionsSheet.addRow(['4. Supplier must match an existing supplier Legal Name exactly (see list below)']);
    instructionsSheet.addRow(['5. License Expiry Date format: YYYY-MM-DD (e.g., 2026-12-31)']);
    instructionsSheet.addRow(['6. Do not modify column headers']);
    instructionsSheet.addRow(['7. Save the file and upload it via the import button']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Notes:']);
    instructionsSheet.addRow(['- Duplicate mobile numbers will be skipped with an error']);
    instructionsSheet.addRow(['- All imported drivers will be set to Active status']);
    instructionsSheet.addRow(['- Maximum 500 drivers per import']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Available Suppliers:']);
    for (const s of suppliers) {
      instructionsSheet.addRow([`  - ${s.legalName}`]);
    }
    instructionsSheet.getRow(1).font = { bold: true, size: 14 };
    instructionsSheet.getRow(3).font = { bold: true };
    instructionsSheet.getRow(12).font = { bold: true };
    instructionsSheet.getRow(17).font = { bold: true };

    // Drivers data sheet
    const driversSheet = workbook.addWorksheet('Drivers');
    driversSheet.columns = [
      { header: 'Name', key: 'name', width: 30 },
      { header: 'Mobile Number', key: 'mobileNumber', width: 20 },
      { header: 'License Number', key: 'licenseNumber', width: 20 },
      { header: 'License Expiry Date', key: 'licenseExpiryDate', width: 20 },
      { header: 'Supplier', key: 'supplier', width: 30 },
    ];

    // Style header row
    const headerRow = driversSheet.getRow(1);
    headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF4472C4' },
    };
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' };

    // Add 3 sample rows for guidance
    const sampleSupplier = suppliers[0]?.legalName || '';
    driversSheet.addRow({
      name: 'Ahmed Hassan',
      mobileNumber: '+20 100 123 4567',
      licenseNumber: 'DL-12345',
      licenseExpiryDate: '2027-06-15',
      supplier: sampleSupplier,
    });
    driversSheet.addRow({
      name: 'Mohamed Ali',
      mobileNumber: '+20 111 987 6543',
      licenseNumber: 'DL-67890',
      licenseExpiryDate: '2026-12-31',
      supplier: '',
    });
    driversSheet.addRow({
      name: 'Ibrahim Saeed',
      mobileNumber: '+20 122 555 1234',
      licenseNumber: '',
      licenseExpiryDate: '',
      supplier: '',
    });

    // Style sample rows in italic gray
    for (let i = 2; i <= 4; i++) {
      const row = driversSheet.getRow(i);
      row.font = { italic: true, color: { argb: 'FF999999' } };
    }

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  // ──────────────────────────────────────────────
  // BULK IMPORT – parse Excel and create drivers
  // ──────────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const driversSheet = workbook.getWorksheet('Drivers');
    if (!driversSheet) {
      throw new BadRequestException('Invalid template: "Drivers" sheet not found');
    }

    // Pre-load suppliers for lookup
    const allSuppliers = await this.prisma.supplier.findMany({
      where: { deletedAt: null },
      select: { id: true, legalName: true },
    });
    const supplierMap = new Map(allSuppliers.map((s) => [s.legalName.toLowerCase(), s.id]));

    const items: { name: string; mobileNumber: string; licenseNumber?: string; licenseExpiryDate?: Date; supplierId?: string }[] = [];
    const errors: string[] = [];

    driversSheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return; // Skip header

      const name = String(row.getCell(1).value || '').trim();
      const mobileNumber = String(row.getCell(2).value || '').trim();
      const licenseNumber = String(row.getCell(3).value || '').trim();
      const licenseExpiryStr = String(row.getCell(4).value || '').trim();
      const supplierName = String(row.getCell(5).value || '').trim();

      // Skip empty rows
      if (!name && !mobileNumber) return;

      // Skip sample rows (italic gray placeholder text)
      if (name === 'Ahmed Hassan' || name === 'Mohamed Ali' || name === 'Ibrahim Saeed') {
        // Only skip if they look like the template samples
        if (mobileNumber.startsWith('+20 1')) return;
      }

      // Validate required fields
      if (!name) {
        errors.push(`Row ${rowNumber}: Name is required`);
        return;
      }
      if (!mobileNumber) {
        errors.push(`Row ${rowNumber}: Mobile Number is required`);
        return;
      }

      // Parse date if provided
      let licenseExpiryDate: Date | undefined;
      if (licenseExpiryStr) {
        const parsed = new Date(licenseExpiryStr);
        if (isNaN(parsed.getTime())) {
          errors.push(`Row ${rowNumber}: Invalid date format "${licenseExpiryStr}" (use YYYY-MM-DD)`);
          return;
        }
        licenseExpiryDate = parsed;
      }

      // Resolve supplier
      let supplierId: string | undefined;
      if (supplierName) {
        supplierId = supplierMap.get(supplierName.toLowerCase());
        if (!supplierId) {
          errors.push(`Row ${rowNumber}: Supplier "${supplierName}" not found — driver will be imported without supplier`);
        }
      }

      items.push({
        name,
        mobileNumber,
        ...(licenseNumber && { licenseNumber }),
        ...(licenseExpiryDate && { licenseExpiryDate }),
        ...(supplierId && { supplierId }),
      });
    });

    if (items.length === 0 && errors.length === 0) {
      throw new BadRequestException('No data found in the Drivers sheet');
    }

    if (items.length > 500) {
      throw new BadRequestException('Maximum 500 drivers per import. Please split into multiple files.');
    }

    // Check for duplicates within the import batch
    const mobilesSeen = new Set<string>();
    const deduped: typeof items = [];
    for (const item of items) {
      if (mobilesSeen.has(item.mobileNumber)) {
        errors.push(`Duplicate mobile "${item.mobileNumber}" in import file — skipped "${item.name}"`);
        continue;
      }
      mobilesSeen.add(item.mobileNumber);
      deduped.push(item);
    }

    // Check for existing mobile numbers in database
    const existingDrivers = await this.prisma.driver.findMany({
      where: {
        mobileNumber: { in: deduped.map((d) => d.mobileNumber) },
        deletedAt: null,
      },
      select: { mobileNumber: true, name: true },
    });

    const existingMobiles = new Set(existingDrivers.map((d) => d.mobileNumber));
    const toCreate: typeof deduped = [];

    for (const item of deduped) {
      if (existingMobiles.has(item.mobileNumber)) {
        errors.push(`Mobile "${item.mobileNumber}" already exists — skipped "${item.name}"`);
        continue;
      }
      toCreate.push(item);
    }

    // Bulk create in a transaction
    if (toCreate.length > 0) {
      await this.prisma.$transaction(
        toCreate.map((d) =>
          this.prisma.driver.create({
            data: {
              name: d.name,
              mobileNumber: d.mobileNumber,
              licenseNumber: d.licenseNumber,
              licenseExpiryDate: d.licenseExpiryDate,
              supplierId: d.supplierId,
            },
          }),
        ),
      );
    }

    return { imported: toCreate.length, errors };
  }
}
