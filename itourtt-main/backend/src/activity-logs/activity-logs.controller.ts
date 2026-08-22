import {
  Controller,
  Get,
  Param,
  ParseUUIDPipe,
  Query,
  Res,
  UseGuards,
} from '@nestjs/common';
import * as express from 'express';
import { ActivityLogsService } from './activity-logs.service.js';
import { QueryActivityLogDto } from './dto/query-activity-log.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';

@Controller('activity-logs')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Permissions('activity-logs')
export class ActivityLogsController {
  constructor(private readonly service: ActivityLogsService) {}

  @Get()
  async findAll(@Query() query: QueryActivityLogDto) {
    return this.service.findAll(query);
  }

  @Get('export')
  @Permissions('activity-logs.export')
  async exportExcel(
    @Query() query: QueryActivityLogDto,
    @Res() res: express.Response,
  ) {
    const buffer = await this.service.exportToExcel(query);
    const date = new Date().toISOString().split('T')[0];
    res.set({
      'Content-Type':
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="activity_log_${date}.xlsx"`,
      'Content-Length': buffer.length.toString(),
    });
    res.end(buffer);
  }

  @Get('entities')
  async getEntities() {
    return this.service.getDistinctEntities();
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.service.findOne(id);
  }
}
