import {
  Controller,
  Delete,
  Get,
  Post,
  Param,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { SessionsService } from './sessions.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';

// Admin "Active sessions" view: list a user's device sessions + force-logout.
@Controller('users/:userId/sessions')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
@Roles('ADMIN')
@Permissions('users')
export class SessionsController {
  constructor(private readonly sessions: SessionsService) {}

  @Get()
  list(@Param('userId') userId: string) {
    return this.sessions.listForUser(userId);
  }

  @Post(':sessionId/logout')
  @HttpCode(HttpStatus.OK)
  forceLogout(
    @Param('userId') userId: string,
    @Param('sessionId') sessionId: string,
  ) {
    return this.sessions.forceLogout(userId, sessionId);
  }

  // Clear a single login session: signs the device out and deletes the record so
  // it can never block the user's next login.
  @Delete(':sessionId')
  @HttpCode(HttpStatus.OK)
  clear(
    @Param('userId') userId: string,
    @Param('sessionId') sessionId: string,
  ) {
    return this.sessions.clear(userId, sessionId);
  }
}
