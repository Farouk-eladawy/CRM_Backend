import {
  Body,
  Controller,
  Get,
  Param,
  Patch,
  Post,
  Query,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { WhatsappNotificationsService } from './whatsapp-notifications.service.js';
import { UpdateWhatsappSettingsDto } from './dto/update-whatsapp-settings.dto.js';
import { UpdateWhatsappTemplateDto } from './dto/update-whatsapp-template.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';

const uploadsDir = path.join(process.cwd(), 'uploads', 'whatsapp');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const uploadStorage = diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (_req, file, cb) => {
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  },
});

@Controller('whatsapp-notifications')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
@Roles('ADMIN')
export class WhatsappNotificationsController {
  constructor(
    private readonly whatsappService: WhatsappNotificationsService,
  ) {}

  @Get('settings')
  @Permissions('whatsapp.settings')
  async getSettings() {
    return this.whatsappService.getSettings();
  }

  @Patch('settings')
  @Permissions('whatsapp.settings.editSettings')
  async updateSettings(@Body() dto: UpdateWhatsappSettingsDto) {
    return this.whatsappService.updateSettings(dto);
  }

  @Get('logs')
  @Permissions('whatsapp.logs')
  async getLogs(
    @Query('page') page?: string,
    @Query('limit') limit?: string,
  ) {
    return this.whatsappService.getLogs(
      Math.max(1, parseInt(page ?? '1', 10) || 1),
      Math.min(100, Math.max(1, parseInt(limit ?? '50', 10) || 50)),
    );
  }

  @Post('test')
  @Permissions('whatsapp.testSend')
  async sendTestMessage(@Body('phone') phone: string) {
    return this.whatsappService.sendTestMessage(phone);
  }

  @Get('templates')
  @Permissions('whatsapp.settings')
  async getTemplates() {
    return this.whatsappService.getTemplates();
  }

  @Patch('templates/:id')
  @Permissions('whatsapp.settings.editSettings')
  async updateTemplate(
    @Param('id') id: string,
    @Body() dto: UpdateWhatsappTemplateDto,
  ) {
    return this.whatsappService.updateTemplate(id, dto);
  }

  @Post('upload-media')
  @Permissions('whatsapp.uploadMedia')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadMedia(@UploadedFile() file: any) {
    const url = '/uploads/whatsapp/' + file.filename;
    await this.whatsappService.updateMediaUrl(url);
    return { url, filename: file.originalname };
  }
}
