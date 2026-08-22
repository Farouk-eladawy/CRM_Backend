import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import * as XLSX from 'xlsx';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class ImportTemplatesService {
  constructor(private readonly prisma: PrismaService) {}

  async findAllByCustomer(customerId: string) {
    return this.prisma.customerImportTemplate.findMany({
      where: { customerId },
      orderBy: { createdAt: 'desc' },
    });
  }

  async create(
    customerId: string,
    serviceType: string,
    notes: string | undefined,
    file: Express.Multer.File,
  ) {
    // Determine file type
    const ext = path.extname(file.originalname).toLowerCase();
    let fileType = 'IMAGE';
    if (ext === '.pdf') fileType = 'PDF';
    else if (ext === '.xlsx' || ext === '.xls') fileType = 'XLSX';

    // Extract sample data for AI context
    let sampleData: unknown = null;
    try {
      if (fileType === 'XLSX') {
        sampleData = this.extractExcelSample(file.path);
      }
    } catch {
      // Non-critical, sample extraction failed
    }

    // Upsert: one template per customer per service type
    const existing = await this.prisma.customerImportTemplate.findUnique({
      where: { customerId_serviceType: { customerId, serviceType: serviceType as any } },
    });

    if (existing) {
      // Delete old file
      try {
        fs.unlinkSync(existing.filePath);
      } catch {
        // File may already be gone
      }

      return this.prisma.customerImportTemplate.update({
        where: { id: existing.id },
        data: {
          fileType,
          fileName: file.originalname,
          filePath: file.path,
          fieldMappings: undefined,
          sampleData: sampleData as any,
          notes,
        },
      });
    }

    return this.prisma.customerImportTemplate.create({
      data: {
        customerId,
        serviceType: serviceType as any,
        fileType,
        fileName: file.originalname,
        filePath: file.path,
        sampleData: sampleData as any,
        notes,
      },
    });
  }

  async remove(customerId: string, templateId: string) {
    const template = await this.prisma.customerImportTemplate.findFirst({
      where: { id: templateId, customerId },
    });

    if (!template) {
      throw new NotFoundException('Template not found');
    }

    // Delete the file
    try {
      fs.unlinkSync(template.filePath);
    } catch {
      // File may already be gone
    }

    await this.prisma.customerImportTemplate.delete({
      where: { id: templateId },
    });

    return { message: 'Template deleted' };
  }

  /**
   * Build context from stored templates for a customer.
   * Used by the AI parser to improve extraction accuracy.
   */
  async getTemplateContext(customerId: string, serviceType?: string) {
    const where: any = { customerId, isActive: true };
    if (serviceType) where.serviceType = serviceType;

    const templates = await this.prisma.customerImportTemplate.findMany({ where });

    return templates.map((t) => ({
      serviceType: t.serviceType,
      fileType: t.fileType,
      fileName: t.fileName,
      sampleData: t.sampleData,
      fieldMappings: t.fieldMappings,
      notes: t.notes,
    }));
  }

  /**
   * Get the file content for a template (for passing to AI)
   */
  async getTemplateFile(customerId: string, serviceType: string) {
    const template = await this.prisma.customerImportTemplate.findUnique({
      where: { customerId_serviceType: { customerId, serviceType: serviceType as any } },
    });

    if (!template) return null;

    if (template.fileType === 'XLSX') {
      return {
        type: 'xlsx' as const,
        data: this.extractExcelSample(template.filePath),
      };
    }

    // For PDF/Image, return the file path for Gemini vision
    return {
      type: template.fileType.toLowerCase() as 'pdf' | 'image',
      filePath: template.filePath,
    };
  }

  private extractExcelSample(filePath: string): Record<string, unknown>[] {
    const workbook = XLSX.readFile(filePath);
    const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(firstSheet) as Record<string, unknown>[];
    // Return first 5 rows as sample
    return rows.slice(0, 5);
  }
}
