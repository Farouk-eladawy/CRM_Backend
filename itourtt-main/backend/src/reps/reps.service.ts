import { Injectable, NotFoundException, ConflictException, BadRequestException } from '@nestjs/common';
import * as bcrypt from 'bcryptjs';
import ExcelJS from 'exceljs';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateRepDto } from './dto/create-rep.dto.js';
import { UpdateRepDto } from './dto/update-rep.dto.js';
import { AssignZoneDto } from './dto/assign-zone.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { PaginatedResponse } from '../common/dto/api-response.dto.js';

@Injectable()
export class RepsService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(pagination: PaginationDto, isActive?: boolean) {
    const { page = 1, limit = 20 } = pagination;
    const skip = (page - 1) * limit;

    const where: { deletedAt: null; isActive?: boolean } = { deletedAt: null };
    if (isActive !== undefined) {
      where.isActive = isActive;
    }

    const [data, total] = await Promise.all([
      this.prisma.rep.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          user: { select: { id: true, email: true, name: true, role: true, isActive: true } },
          repZones: {
            include: {
              zone: {
                include: {
                  city: {
                    include: { airport: true },
                  },
                },
              },
            },
          },
        },
      }),
      this.prisma.rep.count({ where }),
    ]);

    return new PaginatedResponse(data, total, page, limit);
  }

  async findOne(id: string) {
    const rep = await this.prisma.rep.findFirst({
      where: { id, deletedAt: null },
      include: {
        repZones: {
          include: {
            zone: {
              include: {
                city: {
                  include: { airport: true },
                },
              },
            },
          },
        },
      },
    });

    if (!rep) {
      throw new NotFoundException(`Rep with ID "${id}" not found`);
    }

    return rep;
  }

  async getFees(repId: string, from?: string, to?: string) {
    const where: Record<string, unknown> = { repId };
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

    const fees = await this.prisma.repFee.findMany({
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
      },
      orderBy: { createdAt: 'desc' },
    });

    const totalAmount = fees.reduce((sum, f) => sum + Number(f.amount), 0);
    return { fees, totalAmount, count: fees.length };
  }

  async create(dto: CreateRepDto) {
    return this.prisma.rep.create({
      data: {
        name: dto.name,
        mobileNumber: dto.mobileNumber,
        ...(dto.feePerFlight !== undefined && { feePerFlight: dto.feePerFlight }),
      },
    });
  }

  async update(id: string, dto: UpdateRepDto) {
    await this.findOne(id);

    return this.prisma.rep.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.mobileNumber !== undefined && { mobileNumber: dto.mobileNumber }),
        ...(dto.feePerFlight !== undefined && { feePerFlight: dto.feePerFlight }),
      },
    });
  }

  async toggleStatus(id: string) {
    const rep = await this.findOne(id);
    const newStatus = !rep.isActive;

    return this.prisma.$transaction(async (tx) => {
      const updated = await tx.rep.update({
        where: { id },
        data: { isActive: newStatus },
      });

      if (rep.userId) {
        await tx.user.update({
          where: { id: rep.userId },
          data: { isActive: newStatus },
        });
      }

      return updated;
    });
  }

  async softDelete(id: string) {
    const rep = await this.findOne(id);

    return this.prisma.$transaction(async (tx) => {
      await tx.rep.update({
        where: { id },
        data: { deletedAt: new Date(), isActive: false },
      });

      if (rep.userId) {
        await tx.user.update({
          where: { id: rep.userId },
          data: { isActive: false },
        });
      }

      return { success: true };
    });
  }

  async updateAttachment(id: string, url: string) {
    await this.findOne(id);
    return this.prisma.rep.update({
      where: { id },
      data: { attachmentUrl: url },
    });
  }

  async assignZone(repId: string, dto: AssignZoneDto) {
    await this.findOne(repId);

    // Verify zone exists
    const zone = await this.prisma.zone.findFirst({
      where: { id: dto.zoneId, deletedAt: null },
    });
    if (!zone) {
      throw new NotFoundException(`Zone with ID "${dto.zoneId}" not found`);
    }

    // Check if assignment already exists
    const existing = await this.prisma.repZone.findUnique({
      where: {
        repId_zoneId: {
          repId,
          zoneId: dto.zoneId,
        },
      },
    });
    if (existing) {
      throw new ConflictException('This zone is already assigned to this rep');
    }

    return this.prisma.repZone.create({
      data: {
        repId,
        zoneId: dto.zoneId,
      },
      include: {
        zone: {
          include: {
            city: {
              include: { airport: true },
            },
          },
        },
      },
    });
  }

  async unassignZone(repId: string, zoneId: string) {
    const assignment = await this.prisma.repZone.findUnique({
      where: {
        repId_zoneId: {
          repId,
          zoneId,
        },
      },
    });

    if (!assignment) {
      throw new NotFoundException(
        `Zone assignment for rep "${repId}" and zone "${zoneId}" not found`,
      );
    }

    return this.prisma.repZone.delete({
      where: { id: assignment.id },
    });
  }

  async createUserAccount(repId: string, dto: { password: string }) {
    const rep = await this.findOne(repId);

    if (rep.userId) {
      throw new ConflictException('This rep already has a user account');
    }

    if (!rep.mobileNumber) {
      throw new BadRequestException('Rep must have a mobile number to create an account');
    }

    const existingPhone = await this.prisma.user.findUnique({
      where: { phone: rep.mobileNumber },
    });
    if (existingPhone) {
      throw new ConflictException('A user with this mobile number already exists');
    }

    const passwordHash = await bcrypt.hash(dto.password, 12);
    const portalEmail = `rep.${rep.mobileNumber}@portal.itour.local`;

    return this.prisma.$transaction(async (tx) => {
      const user = await tx.user.create({
        data: {
          email: portalEmail,
          phone: rep.mobileNumber,
          passwordHash,
          name: rep.name,
          role: 'REP',
        },
      });

      await tx.rep.update({
        where: { id: repId },
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

  async resetPassword(repId: string, newPassword: string) {
    const rep = await this.findOne(repId);

    if (!rep.userId) {
      throw new BadRequestException('This rep does not have a user account');
    }

    const passwordHash = await bcrypt.hash(newPassword, 12);

    await this.prisma.user.update({
      where: { id: rep.userId },
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
  // EXPORT – all reps to Excel
  // ──────────────────────────────────────────────

  async exportToExcel(): Promise<Buffer> {
    const reps = await this.prisma.rep.findMany({
      where: { deletedAt: null },
      orderBy: { name: 'asc' },
    });

    const rows = reps.map((r) => ({
      Name: r.name,
      'Mobile Number': r.mobileNumber,
      'Fee Per Flight': Number(r.feePerFlight) || 0,
      Status: r.isActive ? 'Active' : 'Inactive',
    }));

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
    XLSX.utils.book_append_sheet(wb, ws, 'Reps');
    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    return Buffer.from(buf);
  }

  // ──────────────────────────────────────────────
  // IMPORT TEMPLATE – generate Excel template
  // ──────────────────────────────────────────────

  async generateImportTemplate(): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';
    workbook.created = new Date();

    // Instructions sheet
    const instructionsSheet = workbook.addWorksheet('Instructions');
    instructionsSheet.columns = [{ width: 80 }];
    instructionsSheet.addRow(['Rep Bulk Import Template']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Instructions:']);
    instructionsSheet.addRow(['1. Fill in rep data in the "Reps" sheet']);
    instructionsSheet.addRow(['2. Name and Mobile Number are required fields']);
    instructionsSheet.addRow(['3. Fee Per Flight is optional (defaults to 0)']);
    instructionsSheet.addRow(['4. Do not modify column headers']);
    instructionsSheet.addRow(['5. Save the file and upload it via the import button']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Notes:']);
    instructionsSheet.addRow(['- Duplicate mobile numbers will be skipped with an error']);
    instructionsSheet.addRow(['- All imported reps will be set to Active status']);
    instructionsSheet.addRow(['- Maximum 500 reps per import']);
    instructionsSheet.getRow(1).font = { bold: true, size: 14 };
    instructionsSheet.getRow(3).font = { bold: true };
    instructionsSheet.getRow(10).font = { bold: true };

    // Reps data sheet
    const repsSheet = workbook.addWorksheet('Reps');
    repsSheet.columns = [
      { header: 'Name', key: 'name', width: 30 },
      { header: 'Mobile Number', key: 'mobileNumber', width: 20 },
      { header: 'Fee Per Flight', key: 'feePerFlight', width: 18 },
    ];

    // Style header row
    const headerRow = repsSheet.getRow(1);
    headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF4472C4' },
    };
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' };

    // Sample rows
    repsSheet.addRow({
      name: 'Ahmed Hassan',
      mobileNumber: '+20 100 123 4567',
      feePerFlight: 150,
    });
    repsSheet.addRow({
      name: 'Mohamed Ali',
      mobileNumber: '+20 111 987 6543',
      feePerFlight: 200,
    });

    // Style sample rows
    for (let i = 2; i <= 3; i++) {
      const row = repsSheet.getRow(i);
      row.font = { italic: true, color: { argb: 'FF999999' } };
    }

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  // ──────────────────────────────────────────────
  // BULK IMPORT – parse Excel and create reps
  // ──────────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const repsSheet = workbook.getWorksheet('Reps');
    if (!repsSheet) {
      throw new BadRequestException('Invalid template: "Reps" sheet not found');
    }

    const items: { name: string; mobileNumber: string; feePerFlight?: number }[] = [];
    const errors: string[] = [];

    repsSheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;

      const name = String(row.getCell(1).value || '').trim();
      const mobileNumber = String(row.getCell(2).value || '').trim();
      const feeRaw = row.getCell(3).value;

      // Skip empty rows
      if (!name && !mobileNumber) return;

      // Skip sample rows
      if (name === 'Ahmed Hassan' || name === 'Mohamed Ali') {
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

      // Parse fee
      let feePerFlight: number | undefined;
      if (feeRaw !== null && feeRaw !== undefined && String(feeRaw).trim() !== '') {
        const parsed = parseFloat(String(feeRaw));
        if (isNaN(parsed) || parsed < 0) {
          errors.push(`Row ${rowNumber}: Invalid fee "${feeRaw}"`);
          return;
        }
        feePerFlight = parsed;
      }

      items.push({
        name,
        mobileNumber,
        ...(feePerFlight !== undefined && { feePerFlight }),
      });
    });

    if (items.length === 0 && errors.length === 0) {
      throw new BadRequestException('No data found in the Reps sheet');
    }

    if (items.length > 500) {
      throw new BadRequestException('Maximum 500 reps per import. Please split into multiple files.');
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
    const existingReps = await this.prisma.rep.findMany({
      where: {
        mobileNumber: { in: deduped.map((r) => r.mobileNumber) },
        deletedAt: null,
      },
      select: { mobileNumber: true },
    });

    const existingMobiles = new Set(existingReps.map((r) => r.mobileNumber));
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
        toCreate.map((r) =>
          this.prisma.rep.create({
            data: {
              name: r.name,
              mobileNumber: r.mobileNumber,
              ...(r.feePerFlight !== undefined && { feePerFlight: r.feePerFlight }),
            },
          }),
        ),
      );
    }

    return { imported: toCreate.length, errors };
  }
}
