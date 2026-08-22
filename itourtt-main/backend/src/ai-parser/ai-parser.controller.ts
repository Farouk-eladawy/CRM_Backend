import {
  Controller,
  Post,
  Body,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  BadRequestException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { AiParserService } from './ai-parser.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

const tempDir = path.join(process.cwd(), 'uploads', 'temp');
if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir, { recursive: true });
}

const ALLOWED_EXTENSIONS = ['.pdf', '.xlsx', '.xls', '.png', '.jpg', '.jpeg'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const tempStorage = diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, tempDir);
  },
  filename: (_req, file, cb) => {
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  },
});

@Controller('ai-parser')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class AiParserController {
  constructor(private readonly aiParserService: AiParserService) {}

  @Post('extract-jobs')
  @Permissions('traffic-jobs.b2b.importJobs')
  @UseInterceptors(
    FileInterceptor('file', {
      storage: tempStorage,
      limits: { fileSize: MAX_FILE_SIZE },
      fileFilter: (_req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        if (ALLOWED_EXTENSIONS.includes(ext)) {
          cb(null, true);
        } else {
          cb(
            new BadRequestException(
              `File type ${ext} is not supported. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
            ),
            false,
          );
        }
      },
    }),
  )
  async extractJobs(
    @UploadedFile() file: Express.Multer.File,
    @Body('customerId') customerId: string,
    @Body('serviceType') serviceType?: string,
  ) {
    if (!file) {
      throw new BadRequestException('File is required');
    }
    if (!customerId) {
      throw new BadRequestException('customerId is required');
    }

    const result = await this.aiParserService.parseDocument(file, customerId, serviceType);
    return new ApiResponse(result, `Extracted ${result.jobs.length} jobs`);
  }
}
