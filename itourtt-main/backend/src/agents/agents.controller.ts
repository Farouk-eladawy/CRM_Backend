import {
  Controller,
  Get,
  Post,
  Put,
  Patch,
  Delete,
  Param,
  Body,
  Query,
  Res,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  ParseUUIDPipe,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import type { Response } from 'express';
import { AgentsService } from './agents.service.js';
import { CreateAgentDto } from './dto/create-agent.dto.js';
import { UpdateAgentDto } from './dto/update-agent.dto.js';
import { UpdateCreditDto } from './dto/update-credit.dto.js';
import { UpdateInvoiceCycleDto } from './dto/update-invoice-cycle.dto.js';
import { CreateDocumentDto } from './dto/create-document.dto.js';
import { BulkAgentPriceListDto } from './dto/agent-price-list.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import { IsOptional } from 'class-validator';
import { Type } from 'class-transformer';

class AgentListQueryDto extends PaginationDto {
  @IsOptional()
  @Type(() => Boolean)
  isActive?: boolean;
}

@Controller('agents')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class AgentsController {
  constructor(private readonly agentsService: AgentsService) {}

  @Get()
  @Permissions('agents')
  async findAll(@Query() query: AgentListQueryDto) {
    const { isActive, ...pagination } = query;
    return this.agentsService.findAll(pagination, isActive);
  }

  @Get('export/excel')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.export')
  async exportExcel(@Res() res: Response) {
    const buffer = await this.agentsService.exportToExcel();
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="agents_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('import/template')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.downloadTemplate')
  async downloadTemplate(@Res() res: Response) {
    const buffer = await this.agentsService.generateImportTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="agents_import_template.xlsx"',
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Post('import/excel')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.import')
  @UseInterceptors(FileInterceptor('file'))
  async importExcel(@UploadedFile() file: any) {
    if (!file) {
      return new ApiResponse({ imported: 0, errors: ['No file uploaded'] }, 'No file uploaded');
    }
    const result = await this.agentsService.importFromExcel(file.buffer);
    const message = result.errors.length > 0
      ? `Imported ${result.imported} agents with ${result.errors.length} errors`
      : `Successfully imported ${result.imported} agents`;
    return new ApiResponse(result, message);
  }

  @Post()
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.addButton')
  async create(@Body() dto: CreateAgentDto) {
    const agent = await this.agentsService.create(dto);
    return new ApiResponse(agent, 'Agent created successfully');
  }

  @Get(':id')
  @Permissions('agents')
  async findOne(@Param('id') id: string) {
    const agent = await this.agentsService.findOne(id);
    return new ApiResponse(agent);
  }

  @Put(':id')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.table.editButton')
  async update(
    @Param('id') id: string,
    @Body() dto: UpdateAgentDto,
  ) {
    const agent = await this.agentsService.update(id, dto);
    return new ApiResponse(agent, 'Agent updated successfully');
  }

  @Patch(':id/status')
  @Roles('ADMIN')
  @Permissions('agents.table.toggleStatus')
  async toggleStatus(@Param('id') id: string) {
    const result = await this.agentsService.toggleStatus(id);
    return new ApiResponse(result, 'Agent status updated successfully');
  }

  @Delete('bulk')
  @Roles('ADMIN')
  @Permissions('agents.table.deleteButton')
  async bulkDelete(@Body() dto: { ids: string[] }) {
    const result = await this.agentsService.bulkDelete(dto.ids);
    return new ApiResponse(result, `${result.deleted} agents deleted successfully`);
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('agents.table.deleteButton')
  async delete(@Param('id') id: string) {
    await this.agentsService.delete(id);
    return new ApiResponse(null, 'Agent deleted successfully');
  }

  @Get(':id/credit-status')
  @Permissions('agents')
  async getCreditStatus(@Param('id') id: string) {
    const status = await this.agentsService.getCreditStatus(id);
    return new ApiResponse(status);
  }

  @Put(':id/credit')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.table.editButton')
  async updateCredit(
    @Param('id') id: string,
    @Body() dto: UpdateCreditDto,
  ) {
    const credit = await this.agentsService.updateCredit(id, dto);
    return new ApiResponse(credit, 'Agent credit terms updated successfully');
  }

  @Put(':id/invoice-cycle')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.table.editButton')
  async updateInvoiceCycle(
    @Param('id') id: string,
    @Body() dto: UpdateInvoiceCycleDto,
  ) {
    const cycle = await this.agentsService.updateInvoiceCycle(id, dto);
    return new ApiResponse(cycle, 'Agent invoice cycle updated successfully');
  }

  @Post(':id/documents')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.table.editButton')
  async createDocument(
    @Param('id') id: string,
    @Body() dto: CreateDocumentDto,
  ) {
    const document = await this.agentsService.createDocument(id, dto);
    return new ApiResponse(document, 'Document uploaded successfully');
  }

  @Get(':id/documents')
  @Permissions('agents')
  async findDocuments(@Param('id') id: string) {
    const documents = await this.agentsService.findDocuments(id);
    return new ApiResponse(documents);
  }

  // ─── Price List ────────────────────────────────

  @Get(':id/price-list')
  @Permissions('agents')
  async getPriceList(@Param('id') id: string) {
    const items = await this.agentsService.getPriceList(id);
    return new ApiResponse(items);
  }

  @Post(':id/price-list')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.table.editButton')
  async upsertPriceList(
    @Param('id') id: string,
    @Body() dto: BulkAgentPriceListDto,
  ) {
    const items = await this.agentsService.upsertPriceItems(id, dto);
    return new ApiResponse(items, 'Agent price list updated successfully');
  }

  @Delete(':id/price-list/:priceItemId')
  @Roles('ADMIN', 'AGENT_MANAGER')
  @Permissions('agents.table.editButton')
  async deletePriceItem(
    @Param('id') id: string,
    @Param('priceItemId') priceItemId: string,
  ) {
    await this.agentsService.deletePriceItem(id, priceItemId);
    return new ApiResponse(null, 'Price item deleted successfully');
  }
}
