import { Injectable, NotFoundException, ConflictException, BadRequestException } from '@nestjs/common';
import ExcelJS from 'exceljs';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateJobServiceTypeDto } from './dto/create-job-service-type.dto.js';

@Injectable()
export class JobServiceTypesService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll() {
    return this.prisma.jobServiceType.findMany({
      where: { isActive: true },
      include: {
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
      },
      orderBy: { name: 'asc' },
    });
  }

  async create(dto: CreateJobServiceTypeDto) {
    const existing = await this.prisma.jobServiceType.findUnique({
      where: { name: dto.name.trim() },
    });
    if (existing) {
      throw new ConflictException(`Service type "${dto.name}" already exists`);
    }
    return this.prisma.jobServiceType.create({
      data: {
        name: dto.name.trim(),
        fromZoneId: dto.fromZoneId ?? null,
        toZoneId: dto.toZoneId ?? null,
        isActive: dto.isActive ?? true,
      },
      include: {
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
      },
    });
  }

  async update(id: string, dto: Partial<CreateJobServiceTypeDto>) {
    const existing = await this.prisma.jobServiceType.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException(`Service type "${id}" not found`);
    return this.prisma.jobServiceType.update({
      where: { id },
      data: {
        ...(dto.name !== undefined && { name: dto.name.trim() }),
        ...(dto.fromZoneId !== undefined && { fromZoneId: dto.fromZoneId }),
        ...(dto.toZoneId !== undefined && { toZoneId: dto.toZoneId }),
        ...(dto.isActive !== undefined && { isActive: dto.isActive }),
      },
      include: {
        fromZone: { select: { id: true, name: true } },
        toZone: { select: { id: true, name: true } },
      },
    });
  }

  async remove(id: string) {
    const existing = await this.prisma.jobServiceType.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException(`Service type "${id}" not found`);
    return this.prisma.jobServiceType.delete({ where: { id } });
  }

  // ─────────────────────────────────────────────────────
  // EXCEL IMPORT
  // ─────────────────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const sheet = workbook.getWorksheet('ServiceTypes');
    if (!sheet) {
      throw new BadRequestException('Invalid file: "ServiceTypes" sheet not found. Use the downloaded template.');
    }

    // Build zone lookup map
    const zones = await this.prisma.zone.findMany({ select: { id: true, name: true } });
    const zoneMap = new Map(zones.map((z) => [z.name.trim().toLowerCase(), z.id]));

    const errors: string[] = [];
    let imported = 0;

    sheet.eachRow(async () => {}); // force parse
    const dataRows: { name: string; fromZone?: string; toZone?: string }[] = [];

    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const name      = String(row.getCell(1).value ?? '').trim();
      const fromZone  = String(row.getCell(2).value ?? '').trim();
      const toZone    = String(row.getCell(3).value ?? '').trim();
      if (!name) return;
      dataRows.push({ name, fromZone: fromZone || undefined, toZone: toZone || undefined });
    });

    if (dataRows.length === 0) throw new BadRequestException('No data rows found in the "ServiceTypes" sheet');
    if (dataRows.length > 500) throw new BadRequestException('Maximum 500 rows per import');

    for (let i = 0; i < dataRows.length; i++) {
      const rowNumber = i + 2;
      const { name, fromZone, toZone } = dataRows[i];

      let fromZoneId: string | undefined;
      let toZoneId: string | undefined;

      if (fromZone) {
        fromZoneId = zoneMap.get(fromZone.toLowerCase());
        if (!fromZoneId) { errors.push(`Row ${rowNumber}: Zone "${fromZone}" not found`); continue; }
      }
      if (toZone) {
        toZoneId = zoneMap.get(toZone.toLowerCase());
        if (!toZoneId) { errors.push(`Row ${rowNumber}: Zone "${toZone}" not found`); continue; }
      }

      try {
        await this.prisma.jobServiceType.upsert({
          where: { name },
          update: { fromZoneId: fromZoneId ?? null, toZoneId: toZoneId ?? null },
          create: { name, fromZoneId: fromZoneId ?? null, toZoneId: toZoneId ?? null },
        });
        imported++;
      } catch (err: any) {
        errors.push(`Row ${rowNumber} "${name}": ${err.message}`);
      }
    }

    return { imported, errors };
  }

  async generateTemplate(): Promise<Buffer> {
    const zones = await this.prisma.zone.findMany({
      select: { name: true, city: { select: { name: true } } },
      orderBy: { name: 'asc' },
    });

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'iTour Transport';

    const inst = workbook.addWorksheet('Instructions');
    inst.columns = [{ width: 80 }];
    inst.addRow(['Job Service Types – Bulk Import Template']).font = { bold: true, size: 14 };
    inst.addRow(['']);
    inst.addRow(['Columns:']).font = { bold: true };
    inst.addRow(['1. Service Type Name  (required) — must be unique']);
    inst.addRow(['2. From Zone Name     (optional) — exact name from the "Zones" sheet']);
    inst.addRow(['3. To Zone Name       (optional) — exact name from the "Zones" sheet']);
    inst.addRow(['']);
    inst.addRow(['Notes:']).font = { bold: true };
    inst.addRow(['- Duplicate names will UPDATE the existing service type (upsert)']);
    inst.addRow(['- Zone columns are optional — leave blank if not applicable']);

    const sheet = workbook.addWorksheet('ServiceTypes');
    sheet.columns = [
      { header: 'Service Type Name', key: 'name',      width: 30 },
      { header: 'From Zone Name',    key: 'fromZone',  width: 25 },
      { header: 'To Zone Name',      key: 'toZone',    width: 25 },
    ];
    const hdr = sheet.getRow(1);
    hdr.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    hdr.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF4472C4' } };
    hdr.alignment = { vertical: 'middle', horizontal: 'center' };
    hdr.height = 22;

    // Sample rows
    const s1 = sheet.addRow({ name: 'ARR-HRG', fromZone: zones[0]?.name ?? '', toZone: zones[1]?.name ?? '' });
    s1.font = { italic: true, color: { argb: 'FF999999' } };
    const s2 = sheet.addRow({ name: 'DEP-HRG', fromZone: zones[1]?.name ?? '', toZone: zones[0]?.name ?? '' });
    s2.font = { italic: true, color: { argb: 'FF999999' } };

    // Zones lookup
    const zonesSheet = workbook.addWorksheet('Zones');
    zonesSheet.columns = [
      { header: 'Zone Name', key: 'name', width: 30 },
      { header: 'City',      key: 'city', width: 25 },
    ];
    zonesSheet.getRow(1).font = { bold: true };
    for (const z of zones) zonesSheet.addRow({ name: z.name, city: z.city?.name ?? '' });

    const buf = await workbook.xlsx.writeBuffer();
    return Buffer.from(buf);
  }
}
