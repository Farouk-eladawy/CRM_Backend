import {
  Controller,
  Get,
  Post,
  Patch,
  Put,
  Delete,
  Body,
  Param,
  UseGuards,
} from '@nestjs/common';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { PermissionsService } from './permissions.service.js';
import { CreateRoleDto } from './dto/create-role.dto.js';
import { UpdateRoleDto } from './dto/update-role.dto.js';
import { SetRolePermissionsDto } from './dto/set-role-permissions.dto.js';

@Controller('permissions')
@UseGuards(JwtAuthGuard, PermissionsGuard)
export class PermissionsController {
  constructor(private readonly permissionsService: PermissionsService) {}

  // ─── PUBLIC (any authenticated user) ───

  @Get('registry')
  getRegistry() {
    return this.permissionsService.getRegistry();
  }

  @Get('mine')
  async getMyPermissions(@CurrentUser('id') userId: string) {
    const keys = await this.permissionsService.getUserPermissionKeys(userId);
    return { permissionKeys: keys };
  }

  // ─── ADMIN ONLY: Role Management ───

  @Get('roles')
  @Permissions('users.roles')
  @Roles('ADMIN')
  async findAllRoles() {
    return this.permissionsService.findAllRoles();
  }

  @Get('roles/:id')
  @Permissions('users.roles')
  @Roles('ADMIN')
  async findRoleById(@Param('id') id: string) {
    return this.permissionsService.findRoleById(id);
  }

  @Post('roles')
  @Permissions('users.roles.addButton')
  @Roles('ADMIN')
  async createRole(@Body() dto: CreateRoleDto) {
    return this.permissionsService.createRole(dto);
  }

  @Patch('roles/:id')
  @Permissions('users.roles.editButton')
  @Roles('ADMIN')
  async updateRole(@Param('id') id: string, @Body() dto: UpdateRoleDto) {
    return this.permissionsService.updateRole(id, dto);
  }

  @Delete('roles/:id')
  @Permissions('users.roles.deleteButton')
  @Roles('ADMIN')
  async deleteRole(@Param('id') id: string) {
    return this.permissionsService.deleteRole(id);
  }

  @Put('roles/:id/permissions')
  @Permissions('users.roles.editPermissions')
  @Roles('ADMIN')
  async setRolePermissions(
    @Param('id') id: string,
    @Body() dto: SetRolePermissionsDto,
  ) {
    return this.permissionsService.setRolePermissions(id, dto.permissionKeys);
  }

  // ─── SEED ───

  @Post('seed')
  @Roles('ADMIN')
  async seedSystemRoles() {
    return this.permissionsService.seedSystemRoles();
  }
}
