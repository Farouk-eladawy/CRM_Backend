import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { PrismaService } from '../prisma/prisma.service.js';
import { ImportTemplatesService } from '../import-templates/import-templates.service.js';
import * as XLSX from 'xlsx';
import * as fs from 'fs';
import * as path from 'path';
import { SELECTABLE_SERVICE_TYPES } from '../common/utils/service-type.util.js';

export interface ParsedJob {
  serviceType: string;
  jobDate: string;
  adultCount: number;
  childCount: number;
  originName: string;
  destinationName: string;
  originAirportId?: string;
  originZoneId?: string;
  originHotelId?: string;
  destinationAirportId?: string;
  destinationZoneId?: string;
  destinationHotelId?: string;
  customerJobId?: string;
  clientName?: string;
  flightNo?: string;
  arrivalTime?: string;
  departureTime?: string;
  pickUpTime?: string;
  notes?: string;
  confidence: number;
  warnings: string[];
  rowIndex: number;
}

interface LocationEntry {
  id: string;
  name: string;
  code?: string;
  parentName?: string;
}

interface LocationIndex {
  airports: LocationEntry[];
  zones: LocationEntry[];
  hotels: LocationEntry[];
}

@Injectable()
export class AiParserService {
  private readonly logger = new Logger(AiParserService.name);
  private genAI: GoogleGenerativeAI | null = null;

  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
    private readonly importTemplatesService: ImportTemplatesService,
  ) {
    const apiKey = this.configService.get<string>('GEMINI_API_KEY');
    if (apiKey) {
      this.genAI = new GoogleGenerativeAI(apiKey);
    }
  }

  async parseDocument(
    file: Express.Multer.File,
    customerId: string,
    serviceType?: string,
  ): Promise<{ jobs: ParsedJob[]; metadata: Record<string, unknown> }> {
    const startTime = Date.now();

    if (!this.genAI) {
      throw new Error('AI parser not configured. Set GEMINI_API_KEY in environment.');
    }

    // 1. Extract raw content based on file type
    const ext = path.extname(file.originalname).toLowerCase();
    let fileContent: string | null = null;
    let fileBase64: string | null = null;
    let fileMimeType: string | null = null;

    if (ext === '.xlsx' || ext === '.xls') {
      fileContent = this.extractExcelContent(file.path);
    } else if (ext === '.pdf') {
      fileBase64 = fs.readFileSync(file.path).toString('base64');
      fileMimeType = 'application/pdf';
    } else if (['.png', '.jpg', '.jpeg'].includes(ext)) {
      fileBase64 = fs.readFileSync(file.path).toString('base64');
      fileMimeType = file.mimetype;
    }

    // 2. Load template context for this customer
    const templateContext = await this.importTemplatesService.getTemplateContext(
      customerId,
      serviceType,
    );

    // 3. Load location reference data
    let locationIndex = await this.buildLocationIndex();

    // 4. Build prompt
    const prompt = this.buildPrompt(templateContext, locationIndex, fileContent, serviceType);

    // 5. Call Gemini
    const model = this.genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

    let rawResponse: string;
    try {
      const parts: any[] = [{ text: prompt }];

      if (fileBase64 && fileMimeType) {
        parts.push({
          inlineData: {
            mimeType: fileMimeType,
            data: fileBase64,
          },
        });
      }

      const result = await model.generateContent(parts);
      rawResponse = result.response.text();
    } catch (error: any) {
      this.logger.error(`Gemini API error: ${error.message}`);
      if (error.message?.includes('429') || error.message?.includes('RATE_LIMIT')) {
        throw new Error('AI service is temporarily busy. Please try again in a minute.');
      }
      throw new Error('Could not parse this document. Please try a cleaner file or a different format.');
    }

    // 6. Parse JSON from response
    let rawJobs: any[];
    try {
      rawJobs = this.extractJsonFromResponse(rawResponse);
    } catch {
      this.logger.error(`Failed to parse AI response: ${rawResponse.substring(0, 500)}`);
      throw new Error('Could not parse AI response. Please try again or use a different file format.');
    }

    if (!rawJobs.length) {
      throw new Error('No transport jobs were found in this document.');
    }

    // 7. Resolve locations and build ParsedJob[]
    const parsedJobs = rawJobs.map((raw, index) =>
      this.resolveAndValidateJob(raw, index, locationIndex),
    );

    // 10. Clean up uploaded file
    try {
      fs.unlinkSync(file.path);
    } catch {
      // Non-critical
    }

    const processingTimeMs = Date.now() - startTime;

    return {
      jobs: parsedJobs,
      metadata: {
        fileName: file.originalname,
        fileType: ext.replace('.', '').toUpperCase(),
        totalExtracted: parsedJobs.length,
        highConfidence: parsedJobs.filter((j) => j.confidence >= 0.8).length,
        lowConfidence: parsedJobs.filter((j) => j.confidence < 0.5).length,
        locationsCreated: 0,
        processingTimeMs,
      },
    };
  }

  private extractExcelContent(filePath: string): string {
    const workbook = XLSX.readFile(filePath);
    const allRows: string[] = [];

    for (const sheetName of workbook.SheetNames) {
      const sheet = workbook.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as unknown[][];
      allRows.push(`=== Sheet: ${sheetName} ===`);
      for (const row of rows) {
        allRows.push((row as any[]).map((c) => String(c ?? '')).join(' | '));
      }
    }

    return allRows.join('\n');
  }

  private async buildLocationIndex(): Promise<LocationIndex> {
    const [airports, zones, hotels] = await Promise.all([
      this.prisma.airport.findMany({
        where: { deletedAt: null },
        select: { id: true, name: true, code: true },
      }),
      this.prisma.zone.findMany({
        where: { deletedAt: null },
        select: { id: true, name: true, city: { select: { name: true } } },
      }),
      this.prisma.hotel.findMany({
        where: { deletedAt: null },
        select: { id: true, name: true, zone: { select: { name: true } } },
      }),
    ]);

    return {
      airports: airports.map((a) => ({ id: a.id, name: a.name, code: a.code })),
      zones: zones.map((z) => ({ id: z.id, name: z.name, parentName: z.city.name })),
      hotels: hotels.map((h) => ({ id: h.id, name: h.name, parentName: h.zone.name })),
    };
  }

  private buildPrompt(
    templateContext: any[],
    locationIndex: LocationIndex,
    fileContent: string | null,
    serviceType?: string,
  ): string {
    const serviceTypes = [...SELECTABLE_SERVICE_TYPES];

    let prompt = `You are a document parser for a transport company in Egypt. Extract all transfer/transport jobs from the following document.

For each job, extract these fields as a JSON object:
- serviceType: one of [${serviceTypes.join(', ')}]${serviceType ? ` (hint: most likely "${serviceType}")` : ''}
- jobDate: in YYYY-MM-DD format
- adultCount: integer (minimum 1, default 1 if not clear)
- childCount: integer (default 0)
- originName: the pickup location name (airport, zone, or hotel)
- originLocationType: one of "AIRPORT", "ZONE", "HOTEL" — classify what type of location the origin is
- originZoneHint: if origin is a hotel, which zone/area/neighborhood is it in (best guess based on name)
- destinationName: the drop-off location name (airport, zone, or hotel)
- destinationLocationType: one of "AIRPORT", "ZONE", "HOTEL" — classify what type of location the destination is
- destinationZoneHint: if destination is a hotel, which zone/area/neighborhood is it in (best guess based on name)
- customerJobId: the customer's own booking/job reference number if available (may be labeled as "Ref", "Booking No", "File No", "Job ID", etc.)
- clientName: passenger/guest name if available
- flightNo: flight number if available (for ARR/DEP services)
- arrivalTime: HH:MM 24-hour format (for ARR services)
- departureTime: HH:MM 24-hour format (for DEP services)
- pickUpTime: HH:MM 24-hour format if mentioned
- notes: any additional notes or special requests

RULES:
- For ARR (arrival) jobs: origin is usually an airport, destination is a hotel/zone
- For DEP (departure) jobs: origin is usually a hotel/zone, destination is an airport
- If the document lists transfers without specifying ARR/DEP, use "ONE_WAY_TRANSFER"
- Parse all dates to YYYY-MM-DD format
- Parse all times to HH:MM 24-hour format
- If adult count is not specified, assume 1
- Extract ALL jobs from the document, do not skip any rows
- For originLocationType and destinationLocationType: airports have names like "Cairo Airport", "SSH", "HRG"; hotels have names like "Hilton", "Marriott", "Resort"; zones are area names like "Naama Bay", "El Gouna"
- For zoneHint fields: use the KNOWN ZONES list below to pick the closest matching zone name, or leave empty if unsure
`;

    // Add template context if available
    if (templateContext.length > 0) {
      prompt += '\n--- CUSTOMER TEMPLATE CONTEXT ---\n';
      prompt += 'This customer typically sends files in this format:\n';
      for (const t of templateContext) {
        prompt += `Service type: ${t.serviceType}, File type: ${t.fileType}`;
        if (t.notes) prompt += `, Notes: ${t.notes}`;
        if (t.sampleData) {
          prompt += `\nSample data from their previous file:\n${JSON.stringify(t.sampleData, null, 2)}\n`;
        }
        prompt += '\n';
      }
    }

    // Add known locations
    prompt += '\n--- KNOWN LOCATIONS ---\n';
    prompt += 'AIRPORTS:\n';
    for (const a of locationIndex.airports) {
      prompt += `- ${a.name} (code: ${a.code})\n`;
    }
    prompt += '\nZONES:\n';
    for (const z of locationIndex.zones) {
      prompt += `- ${z.name} (city: ${z.parentName})\n`;
    }
    prompt += '\nHOTELS:\n';
    for (const h of locationIndex.hotels) {
      prompt += `- ${h.name} (zone: ${h.parentName})\n`;
    }

    prompt += `\nIMPORTANT: Use the exact names from KNOWN LOCATIONS when possible. If a location in the document is NOT in the known list, still include it with its original name.

Return ONLY a valid JSON array. Each element must have the fields listed above.
Do not include any explanatory text, markdown formatting, or code fences outside the JSON array.
`;

    // Add file content for Excel/text-based files
    if (fileContent) {
      prompt += '\n--- DOCUMENT CONTENT ---\n';
      prompt += fileContent;
    } else {
      prompt += '\n--- DOCUMENT ---\nThe document is attached as an image/PDF. Extract all jobs from it.\n';
    }

    return prompt;
  }

  private extractJsonFromResponse(response: string): any[] {
    // Try to extract JSON array from the response
    let cleaned = response.trim();

    // Remove markdown code fences if present
    if (cleaned.startsWith('```json')) {
      cleaned = cleaned.slice(7);
    } else if (cleaned.startsWith('```')) {
      cleaned = cleaned.slice(3);
    }
    if (cleaned.endsWith('```')) {
      cleaned = cleaned.slice(0, -3);
    }
    cleaned = cleaned.trim();

    // Try direct parse
    const parsed = JSON.parse(cleaned);
    if (Array.isArray(parsed)) return parsed;
    if (parsed.jobs && Array.isArray(parsed.jobs)) return parsed.jobs;

    throw new Error('Response is not a JSON array');
  }

  private resolveAndValidateJob(
    raw: any,
    index: number,
    locationIndex: LocationIndex,
  ): ParsedJob {
    const warnings: string[] = [];
    let confidence = 1.0;

    // Validate required fields
    const serviceType = raw.serviceType || 'ONE_WAY_TRANSFER';
    const jobDate = raw.jobDate || '';
    const adultCount = parseInt(raw.adultCount) || 1;
    const childCount = parseInt(raw.childCount) || 0;

    if (!jobDate) {
      warnings.push('Missing job date');
      confidence -= 0.3;
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(jobDate)) {
      warnings.push(`Invalid date format: ${jobDate}`);
      confidence -= 0.2;
    }

    // Resolve origin location
    const originName = String(raw.originName || '').trim();
    const originResolved = this.resolveLocation(originName, locationIndex);
    let originAirportId: string | undefined;
    let originZoneId: string | undefined;
    let originHotelId: string | undefined;

    if (originResolved) {
      if (originResolved.type === 'airport') originAirportId = originResolved.id;
      else if (originResolved.type === 'zone') originZoneId = originResolved.id;
      else if (originResolved.type === 'hotel') originHotelId = originResolved.id;
    } else if (originName) {
      warnings.push(`Could not match origin "${originName}" to any known location`);
      confidence -= 0.2;
    } else {
      warnings.push('Missing origin location');
      confidence -= 0.3;
    }

    // Resolve destination location
    const destinationName = String(raw.destinationName || '').trim();
    const destResolved = this.resolveLocation(destinationName, locationIndex);
    let destinationAirportId: string | undefined;
    let destinationZoneId: string | undefined;
    let destinationHotelId: string | undefined;

    if (destResolved) {
      if (destResolved.type === 'airport') destinationAirportId = destResolved.id;
      else if (destResolved.type === 'zone') destinationZoneId = destResolved.id;
      else if (destResolved.type === 'hotel') destinationHotelId = destResolved.id;
    } else if (destinationName) {
      warnings.push(`Could not match destination "${destinationName}" to any known location`);
      confidence -= 0.2;
    } else {
      warnings.push('Missing destination location');
      confidence -= 0.3;
    }

    confidence = Math.max(0, Math.min(1, confidence));

    return {
      serviceType,
      jobDate,
      adultCount,
      childCount,
      originName,
      destinationName,
      originAirportId,
      originZoneId,
      originHotelId,
      destinationAirportId,
      destinationZoneId,
      destinationHotelId,
      customerJobId: raw.customerJobId || undefined,
      clientName: raw.clientName || undefined,
      flightNo: raw.flightNo || undefined,
      arrivalTime: raw.arrivalTime || undefined,
      departureTime: raw.departureTime || undefined,
      pickUpTime: raw.pickUpTime || undefined,
      notes: raw.notes || undefined,
      confidence,
      warnings,
      rowIndex: index,
    };
  }

  private resolveLocation(
    name: string,
    index: LocationIndex,
  ): { type: string; id: string } | null {
    if (!name) return null;

    const lower = name.toLowerCase().trim();

    // 1. Exact match on airport code
    const airportByCode = index.airports.find(
      (a) => a.code?.toLowerCase() === lower,
    );
    if (airportByCode) return { type: 'airport', id: airportByCode.id };

    // 2. Airport name match (exact then contains)
    const airportByName = index.airports.find(
      (a) => a.name.toLowerCase() === lower,
    );
    if (airportByName) return { type: 'airport', id: airportByName.id };

    const airportContains = index.airports.find(
      (a) =>
        lower.includes(a.name.toLowerCase()) ||
        a.name.toLowerCase().includes(lower),
    );
    if (airportContains) return { type: 'airport', id: airportContains.id };

    // 3. Hotel name match (exact then contains)
    const hotelByName = index.hotels.find(
      (h) => h.name.toLowerCase() === lower,
    );
    if (hotelByName) return { type: 'hotel', id: hotelByName.id };

    const hotelContains = index.hotels.find(
      (h) =>
        lower.includes(h.name.toLowerCase()) ||
        h.name.toLowerCase().includes(lower),
    );
    if (hotelContains) return { type: 'hotel', id: hotelContains.id };

    // 4. Zone name match (exact then contains)
    const zoneByName = index.zones.find(
      (z) => z.name.toLowerCase() === lower,
    );
    if (zoneByName) return { type: 'zone', id: zoneByName.id };

    const zoneContains = index.zones.find(
      (z) =>
        lower.includes(z.name.toLowerCase()) ||
        z.name.toLowerCase().includes(lower),
    );
    if (zoneContains) return { type: 'zone', id: zoneContains.id };

    return null;
  }
}
