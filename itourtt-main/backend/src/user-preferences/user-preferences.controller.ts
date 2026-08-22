import { Controller, Get, Put, Param, Body, UseGuards, Req } from '@nestjs/common';
import { UserPreferencesService } from './user-preferences.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';

@Controller('user-preferences')
@UseGuards(JwtAuthGuard)
export class UserPreferencesController {
  constructor(private service: UserPreferencesService) {}

  @Get(':key')
  async get(@Param('key') key: string, @Req() req: any) {
    const value = await this.service.get(req.user.id, key);
    return { value };
  }

  @Put(':key')
  async set(
    @Param('key') key: string,
    @Body() body: { value: unknown },
    @Req() req: any,
  ) {
    await this.service.set(req.user.id, key, body.value);
    return { ok: true };
  }
}
