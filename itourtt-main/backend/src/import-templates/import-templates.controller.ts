import {
  Controller,
  Get,
  Post,
  Delete,
  Param,
  Body,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  ParseUUIDPipe,
  BadRequestException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { ImportTemplatesService } from './import-templates.service.js';
import { CreateTemplateDto } from './dto/create-template.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

const templatesDir = path.join(process.cwd(), 'uploads', 'templates');
if (!fs.existsSync(templatesDir)) {
  fs.mkdirSync(templatesDir, { recursive: true });
}

const ALLOWED_EXTENSIONS = ['.pdf', '.xlsx', '.xls', '.png', '.jpg', '.jpeg'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const templateStorage = diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, templatesDir);
  },
  filename: (_req, file, cb) => {
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  },
});

@Controller('customers/:customerId/import-templates')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class ImportTemplatesController {
  constructor(private readonly importTemplatesService: ImportTemplatesService) {}

  @Get()
  @Permissions('customers.detail.importTemplates')
  async findAll(@Param('customerId') customerId: string) {
    const templates = await this.importTemplatesService.findAllByCustomer(customerId);
    return new ApiResponse(templates);
  }

  @Post()
  @Permissions('customers.detail.importTemplates.upload')
  @UseInterceptors(
    FileInterceptor('file', {
      storage: templateStorage,
      limits: { fileSize: MAX_FILE_SIZE },
      fileFilter: (_req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        if (ALLOWED_EXTENSIONS.includes(ext)) {
          cb(null, true);
        } else {
          cb(new BadRequestException(`File type ${ext} is not supported. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`), false);
        }
      },
    }),
  )
  async create(
    @Param('customerId') customerId: string,
    @Body() dto: CreateTemplateDto,
    @UploadedFile() file: Express.Multer.File,
  ) {
    if (!file) {
      throw new BadRequestException('File is required');
    }

    const template = await this.importTemplatesService.create(
      customerId,
      dto.serviceType,
      dto.notes,
      file,
    );

    return new ApiResponse(template, 'Template uploaded successfully');
  }

  @Delete(':id')
  @Permissions('customers.detail.importTemplates.delete')
  async remove(
    @Param('customerId') customerId: string,
    @Param('id') id: string,
  ) {
    const result = await this.importTemplatesService.remove(customerId, id);
    return new ApiResponse(result);
  }
}
