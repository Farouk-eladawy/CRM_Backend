import {
  Controller,
  Get,
  Patch,
  Delete,
  Param,
  Body,
  Query,
  UseGuards,
} from '@nestjs/common';
import { IsBoolean } from 'class-validator';
import { ContactMessagesService } from './contact-messages.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

class SetReadDto {
  @IsBoolean() isRead!: boolean;
}

@Controller('admin/contact-messages')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
@Permissions('contact-messages')
export class ContactMessagesAdminController {
  constructor(private readonly service: ContactMessagesService) {}

  @Get()
  async list(@Query('unread') unread?: string) {
    return new ApiResponse(await this.service.list(unread === 'true'));
  }

  @Get('unread-count')
  async unreadCount() {
    return new ApiResponse(await this.service.unreadCount());
  }

  @Patch(':id/read')
  async setRead(@Param('id') id: string, @Body() dto: SetReadDto) {
    return new ApiResponse(await this.service.setRead(id, dto.isRead), 'Saved.');
  }

  @Delete(':id')
  async remove(@Param('id') id: string) {
    return new ApiResponse(await this.service.remove(id), 'Deleted.');
  }
}
