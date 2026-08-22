import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import ExcelJS from 'exceljs';
import * as XLSX from 'xlsx';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateAgentDto } from './dto/create-agent.dto.js';
import { UpdateAgentDto } from './dto/update-agent.dto.js';
import { UpdateCreditDto } from './dto/update-credit.dto.js';
import { UpdateInvoiceCycleDto } from './dto/update-invoice-cycle.dto.js';
import { CreateDocumentDto } from './dto/create-document.dto.js';
import { BulkAgentPriceListDto, AgentPriceItemDto } from './dto/agent-price-list.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { PaginatedResponse } from '../common/dto/api-response.dto.js';
import type { Currency, InvoiceCycleType, DocumentType, ServiceType } from '../../generated/prisma/enums.js';

@Injectable()
export class AgentsService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(pagination: PaginationDto, isActive?: boolean) {
    const { page = 1, limit = 20 } = pagination;
    const skip = (page - 1) * limit;

    const where: Record<string, unknown> = { deletedAt: null };
    if (isActive !== undefined) {
      where.isActive = isActive;
    }

    const [data, total] = await Promise.all([
      this.prisma.agent.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          creditTerms: true,
          invoiceCycle: true,
        },
      }),
      this.prisma.agent.count({ where }),
    ]);

    return new PaginatedResponse(data, total, page, limit);
  }

  async findOne(id: string) {
    const agent = await this.prisma.agent.findFirst({
      where: { id, deletedAt: null },
      include: {
        creditTerms: true,
        invoiceCycle: true,
        documents: {
          orderBy: { createdAt: 'desc' },
        },
      },
    });

    if (!agent) {
      throw new NotFoundException(`Agent with ID "${id}" not found`);
    }

    return agent;
  }

  async create(dto: CreateAgentDto) {
    return this.prisma.agent.create({
      data: {
        legalName: dto.legalName,
        tradeName: dto.tradeName,
        taxId: dto.taxId,
        address: dto.address,
        city: dto.city,
        country: dto.country,
        phone: dto.phone,
        email: dto.email,
        ...(dto.currency && { currency: dto.currency as Currency }),
        refPattern: dto.refPattern ?? null,
        refExample: dto.refExample ?? null,
      },
      include: {
        creditTerms: true,
        invoiceCycle: true,
      },
    });
  }

  async update(id: string, dto: UpdateAgentDto) {
    await this.findOne(id);

    return this.prisma.agent.update({
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
        ...(dto.currency !== undefined && { currency: dto.currency as Currency }),
        ...(dto.refPattern !== undefined && { refPattern: dto.refPattern }),
        ...(dto.refExample !== undefined && { refExample: dto.refExample }),
      },
      include: {
        creditTerms: true,
        invoiceCycle: true,
        documents: true,
      },
    });
  }

  async toggleStatus(id: string) {
    const agent = await this.findOne(id);

    return this.prisma.agent.update({
      where: { id },
      data: { isActive: !agent.isActive },
    });
  }

  async delete(id: string) {
    await this.findOne(id);

    return this.prisma.agent.update({
      where: { id },
      data: { deletedAt: new Date() },
    });
  }

  async bulkDelete(ids: string[]) {
    if (!ids || ids.length === 0) {
      throw new BadRequestException('No agent IDs provided');
    }

    const result = await this.prisma.agent.updateMany({
      where: { id: { in: ids }, deletedAt: null },
      data: { deletedAt: new Date() },
    });

    return { deleted: result.count };
  }

  async getCreditStatus(agentId: string) {
    const agent = await this.findOne(agentId);
    const creditTerms = await this.prisma.agentCreditTerms.findUnique({
      where: { agentId },
    });

    const outstandingResult = await this.prisma.agentInvoice.aggregate({
      where: {
        agentId,
        status: { in: ['DRAFT', 'POSTED'] as any },
      },
      _sum: { total: true },
    });

    const creditLimit = creditTerms ? Number(creditTerms.creditLimit) : 0;
    const creditDays = creditTerms ? creditTerms.creditDays : 0;
    const outstandingBalance = Number(outstandingResult._sum.total || 0);
    const availableCredit = Math.max(0, creditLimit - outstandingBalance);
    const utilizationPercent =
      creditLimit > 0
        ? parseFloat(((outstandingBalance / creditLimit) * 100).toFixed(1))
        : 0;

    return {
      agentId,
      agentName: agent.legalName,
      creditLimit,
      creditDays,
      outstandingBalance,
      availableCredit,
      utilizationPercent,
    };
  }

  async updateCredit(agentId: string, dto: UpdateCreditDto) {
    await this.findOne(agentId);

    return this.prisma.agentCreditTerms.upsert({
      where: { agentId },
      create: {
        agentId,
        creditLimit: dto.creditLimit,
        creditDays: dto.creditDays,
      },
      update: {
        creditLimit: dto.creditLimit,
        creditDays: dto.creditDays,
      },
    });
  }

  async updateInvoiceCycle(agentId: string, dto: UpdateInvoiceCycleDto) {
    await this.findOne(agentId);

    return this.prisma.agentInvoiceCycle.upsert({
      where: { agentId },
      create: {
        agentId,
        cycleType: dto.cycleType as InvoiceCycleType,
        dayOfWeek: dto.dayOfWeek,
        dayOfMonth: dto.dayOfMonth,
      },
      update: {
        cycleType: dto.cycleType as InvoiceCycleType,
        dayOfWeek: dto.dayOfWeek,
        dayOfMonth: dto.dayOfMonth,
      },
    });
  }

  async createDocument(agentId: string, dto: CreateDocumentDto) {
    await this.findOne(agentId);

    return this.prisma.agentDocument.create({
      data: {
        agentId,
        documentType: dto.documentType as DocumentType,
        fileUrl: dto.fileUrl,
        fileName: dto.fileName,
        ...(dto.expiresAt && { expiresAt: new Date(dto.expiresAt) }),
      },
    });
  }

  async findDocuments(agentId: string) {
    await this.findOne(agentId);

    return this.prisma.agentDocument.findMany({
      where: { agentId },
      orderBy: { createdAt: 'desc' },
    });
  }

  // ─── Price List (Bulk Upsert Pattern) ───────────────────────

  async getPriceList(agentId: string) {
    const agent = await this.prisma.agent.findFirst({
      where: { id: agentId, deletedAt: null },
    });

    if (!agent) {
      throw new NotFoundException(`Agent with id ${agentId} not found`);
    }

    return this.prisma.agentPriceItem.findMany({
      where: { agentId },
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
  }

  async upsertPriceItems(agentId: string, dto: BulkAgentPriceListDto) {
    const agent = await this.prisma.agent.findFirst({
      where: { id: agentId, deletedAt: null },
    });

    if (!agent) {
      throw new NotFoundException(`Agent with id ${agentId} not found`);
    }

    const results = await this.prisma.$transaction(
      dto.items.map((item: AgentPriceItemDto) =>
        this.prisma.agentPriceItem.upsert({
          where: {
            agentId_serviceType_fromZoneId_toZoneId_vehicleTypeId: {
              agentId,
              serviceType: item.serviceType as ServiceType,
              fromZoneId: item.fromZoneId,
              toZoneId: item.toZoneId,
              vehicleTypeId: item.vehicleTypeId,
            },
          },
          create: {
            agentId,
            serviceType: item.serviceType as ServiceType,
            fromZoneId: item.fromZoneId,
            toZoneId: item.toZoneId,
            vehicleTypeId: item.vehicleTypeId,
            price: item.price,
            driverTip: item.driverTip,
            boosterSeatPrice: item.boosterSeatPrice ?? 0,
            babySeatPrice: item.babySeatPrice ?? 0,
            wheelChairPrice: item.wheelChairPrice ?? 0,
            effectiveFrom: item.effectiveFrom ? new Date(item.effectiveFrom) : null,
            effectiveTo: item.effectiveTo ? new Date(item.effectiveTo) : null,
          },
          update: {
            price: item.price,
            driverTip: item.driverTip,
            boosterSeatPrice: item.boosterSeatPrice ?? 0,
            babySeatPrice: item.babySeatPrice ?? 0,
            wheelChairPrice: item.wheelChairPrice ?? 0,
            effectiveFrom: item.effectiveFrom ? new Date(item.effectiveFrom) : null,
            effectiveTo: item.effectiveTo ? new Date(item.effectiveTo) : null,
          },
        }),
      ),
    );

    return results;
  }

  async deletePriceItem(agentId: string, priceItemId: string) {
    const agent = await this.prisma.agent.findFirst({
      where: { id: agentId, deletedAt: null },
    });

    if (!agent) {
      throw new NotFoundException(`Agent with id ${agentId} not found`);
    }

    const priceItem = await this.prisma.agentPriceItem.findFirst({
      where: { id: priceItemId, agentId },
    });

    if (!priceItem) {
      throw new NotFoundException(`Price item with id "${priceItemId}" not found for this agent`);
    }

    return this.prisma.agentPriceItem.delete({
      where: { id: priceItemId },
    });
  }

  // ──────────────────────────────────────────────
  // EXPORT – all agents to Excel
  // ──────────────────────────────────────────────

  async exportToExcel(): Promise<Buffer> {
    const agents = await this.prisma.agent.findMany({
      where: { deletedAt: null },
      orderBy: { legalName: 'asc' },
      include: { creditTerms: true },
    });

    const rows = agents.map((a) => ({
      'Legal Name': a.legalName,
      'Trade Name': a.tradeName || '',
      'Tax ID': a.taxId || '',
      Address: a.address || '',
      City: a.city || '',
      Country: a.country || '',
      Phone: a.phone || '',
      Email: a.email || '',
      Currency: a.currency,
      'Ref Pattern': a.refPattern || '',
      'Ref Example': a.refExample || '',
      'Credit Limit': a.creditTerms ? Number(a.creditTerms.creditLimit) : '',
      'Credit Days': a.creditTerms ? a.creditTerms.creditDays : '',
      Status: a.isActive ? 'Active' : 'Inactive',
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
    XLSX.utils.book_append_sheet(wb, ws, 'Agents');
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
    instructionsSheet.addRow(['Agent Bulk Import Template']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Instructions:']);
    instructionsSheet.addRow(['1. Fill in agent data in the "Agents" sheet']);
    instructionsSheet.addRow(['2. Legal Name is the only required field']);
    instructionsSheet.addRow(['3. Currency must be one of: EGP, USD, EUR, GBP, SAR (defaults to EGP)']);
    instructionsSheet.addRow(['4. Credit Limit and Credit Days are optional numeric values']);
    instructionsSheet.addRow(['5. Do not modify column headers']);
    instructionsSheet.addRow(['6. Save the file and upload it via the import button']);
    instructionsSheet.addRow(['']);
    instructionsSheet.addRow(['Notes:']);
    instructionsSheet.addRow(['- All imported agents will be set to Active status']);
    instructionsSheet.addRow(['- Maximum 500 agents per import']);
    instructionsSheet.getRow(1).font = { bold: true, size: 14 };
    instructionsSheet.getRow(3).font = { bold: true };
    instructionsSheet.getRow(11).font = { bold: true };

    // Agents data sheet
    const agentsSheet = workbook.addWorksheet('Agents');
    agentsSheet.columns = [
      { header: 'Legal Name', key: 'legalName', width: 30 },
      { header: 'Trade Name', key: 'tradeName', width: 25 },
      { header: 'Tax ID', key: 'taxId', width: 20 },
      { header: 'Address', key: 'address', width: 30 },
      { header: 'City', key: 'city', width: 20 },
      { header: 'Country', key: 'country', width: 20 },
      { header: 'Phone', key: 'phone', width: 20 },
      { header: 'Email', key: 'email', width: 25 },
      { header: 'Currency', key: 'currency', width: 12 },
      { header: 'Ref Pattern', key: 'refPattern', width: 20 },
      { header: 'Ref Example', key: 'refExample', width: 20 },
      { header: 'Credit Limit', key: 'creditLimit', width: 15 },
      { header: 'Credit Days', key: 'creditDays', width: 15 },
    ];

    // Style header row
    const headerRow = agentsSheet.getRow(1);
    headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF4472C4' },
    };
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' };

    // Add sample rows
    agentsSheet.addRow({
      legalName: 'Nile Travel Agency',
      tradeName: 'Nile Tours',
      taxId: '123-456-789',
      address: '10 Nile St, Downtown',
      city: 'Cairo',
      country: 'Egypt',
      phone: '+20 2 1234 5678',
      email: 'info@niletravel.com',
      currency: 'EGP',
      refPattern: 'NT-####',
      refExample: 'NT-0001',
      creditLimit: 50000,
      creditDays: 30,
    });
    agentsSheet.addRow({
      legalName: 'Global Transfers Ltd',
      tradeName: '',
      taxId: '',
      address: '',
      city: '',
      country: '',
      phone: '',
      email: '',
      currency: 'USD',
      refPattern: '',
      refExample: '',
      creditLimit: '',
      creditDays: '',
    });

    // Style sample rows
    for (let i = 2; i <= 3; i++) {
      const row = agentsSheet.getRow(i);
      row.font = { italic: true, color: { argb: 'FF999999' } };
    }

    const buffer = await workbook.xlsx.writeBuffer();
    return Buffer.from(buffer);
  }

  // ──────────────────────────────────────────────
  // BULK IMPORT – parse Excel and create agents
  // ──────────────────────────────────────────────

  async importFromExcel(fileBuffer: Buffer): Promise<{ imported: number; errors: string[] }> {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(fileBuffer as unknown as ExcelJS.Buffer);

    const agentsSheet = workbook.getWorksheet('Agents');
    if (!agentsSheet) {
      throw new BadRequestException('Invalid template: "Agents" sheet not found');
    }

    const validCurrencies = new Set(['EGP', 'USD', 'EUR', 'GBP', 'SAR']);

    const items: {
      legalName: string; tradeName?: string; taxId?: string; address?: string;
      city?: string; country?: string; phone?: string; email?: string;
      currency: string; refPattern?: string; refExample?: string;
      creditLimit?: number; creditDays?: number;
    }[] = [];
    const errors: string[] = [];

    agentsSheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;

      const legalName = String(row.getCell(1).value || '').trim();
      const tradeName = String(row.getCell(2).value || '').trim();
      const taxId = String(row.getCell(3).value || '').trim();
      const address = String(row.getCell(4).value || '').trim();
      const city = String(row.getCell(5).value || '').trim();
      const country = String(row.getCell(6).value || '').trim();
      const phone = String(row.getCell(7).value || '').trim();
      const email = String(row.getCell(8).value || '').trim();
      const currency = String(row.getCell(9).value || 'EGP').trim().toUpperCase();
      const refPattern = String(row.getCell(10).value || '').trim();
      const refExample = String(row.getCell(11).value || '').trim();
      const creditLimitRaw = row.getCell(12).value;
      const creditDaysRaw = row.getCell(13).value;

      if (!legalName) return; // Skip empty rows

      // Skip sample rows
      if (legalName === 'Nile Travel Agency' || legalName === 'Global Transfers Ltd') {
        return;
      }

      if (!validCurrencies.has(currency)) {
        errors.push(`Row ${rowNumber}: Invalid currency "${currency}" (use EGP, USD, EUR, GBP, or SAR)`);
        return;
      }

      let creditLimit: number | undefined;
      if (creditLimitRaw !== null && creditLimitRaw !== undefined && String(creditLimitRaw).trim() !== '') {
        creditLimit = parseFloat(String(creditLimitRaw));
        if (isNaN(creditLimit) || creditLimit < 0) {
          errors.push(`Row ${rowNumber}: Invalid credit limit "${creditLimitRaw}"`);
          return;
        }
      }

      let creditDays: number | undefined;
      if (creditDaysRaw !== null && creditDaysRaw !== undefined && String(creditDaysRaw).trim() !== '') {
        creditDays = parseInt(String(creditDaysRaw), 10);
        if (isNaN(creditDays) || creditDays < 0) {
          errors.push(`Row ${rowNumber}: Invalid credit days "${creditDaysRaw}"`);
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
        currency,
        ...(refPattern && { refPattern }),
        ...(refExample && { refExample }),
        ...(creditLimit !== undefined && { creditLimit }),
        ...(creditDays !== undefined && { creditDays }),
      });
    });

    if (items.length === 0 && errors.length === 0) {
      throw new BadRequestException('No data found in the Agents sheet');
    }

    if (items.length > 500) {
      throw new BadRequestException('Maximum 500 agents per import. Please split into multiple files.');
    }

    let imported = 0;
    for (const item of items) {
      try {
        const agent = await this.prisma.agent.create({
          data: {
            legalName: item.legalName,
            tradeName: item.tradeName,
            taxId: item.taxId,
            address: item.address,
            city: item.city,
            country: item.country,
            phone: item.phone,
            email: item.email,
            currency: item.currency as Currency,
            refPattern: item.refPattern,
            refExample: item.refExample,
          },
        });

        // Create credit terms if provided
        if (item.creditLimit !== undefined || item.creditDays !== undefined) {
          await this.prisma.agentCreditTerms.create({
            data: {
              agentId: agent.id,
              creditLimit: item.creditLimit ?? 0,
              creditDays: item.creditDays ?? 0,
            },
          });
        }

        imported++;
      } catch (err: any) {
        errors.push(`Failed "${item.legalName}": ${err.message}`);
      }
    }

    return { imported, errors };
  }
}
