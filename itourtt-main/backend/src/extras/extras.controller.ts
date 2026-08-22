import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Body,
  Param,
  UseGuards,
} from '@nestjs/common';
import { ExtrasService } from './extras.service.js';
import { UpsertExtraDto } from './dto/upsert-extra.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

@Controller('extras')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class ExtrasController {
  constructor(private readonly extrasService: ExtrasService) {}

  @Get()
  @Permissions('extras')
  async findAll() {
    const data = await this.extrasService.findAll();
    return new ApiResponse(data);
  }

  // Active extras for operator selection on a job — authenticated, but NOT gated
  // by the 'extras' management permission (any dispatch/online operator can pick).
  @Get('selectable')
  async selectable() {
    const data = await this.extrasService.getSelectable();
    return new ApiResponse(data);
  }

  @Post()
  @Roles('ADMIN')
  @Permissions('extras.addButton')
  async create(@Body() dto: UpsertExtraDto) {
    const data = await this.extrasService.create(dto);
    return new ApiResponse(data, 'Extra created');
  }

  @Patch(':id')
  @Roles('ADMIN')
  @Permissions('extras.editButton')
  async update(@Param('id') id: string, @Body() dto: UpsertExtraDto) {
    const data = await this.extrasService.update(id, dto);
    return new ApiResponse(data, 'Extra updated');
  }

  @Patch(':id/status')
  @Roles('ADMIN')
  @Permissions('extras.editButton')
  async toggleStatus(@Param('id') id: string) {
    const data = await this.extrasService.toggleStatus(id);
    return new ApiResponse(data, 'Extra status updated');
  }

  @Delete(':id')
  @Roles('ADMIN')
  @Permissions('extras.deleteButton')
  async remove(@Param('id') id: string) {
    const data = await this.extrasService.remove(id);
    return new ApiResponse(data, 'Extra removed');
  }
}
