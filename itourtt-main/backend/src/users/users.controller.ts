import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseEnumPipe,
  ParseUUIDPipe,
  Patch,
  Post,
  Put,
  Query,
  UseGuards,
} from '@nestjs/common';
import { UsersService } from './users.service.js';
import { RolePermissionsService } from './role-permissions.service.js';
import { CreateUserDto } from './dto/create-user.dto.js';
import { UpdateUserDto } from './dto/update-user.dto.js';
import { UpdateRoleDto } from './dto/update-role.dto.js';
import { ChangePasswordDto } from './dto/change-password.dto.js';
import { UpdateRolePermissionsDto } from './dto/update-role-permissions.dto.js';
import { PaginationDto } from '../common/dto/pagination.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { UserRole } from '../../generated/prisma/enums.js';

@Controller('users')
@UseGuards(JwtAuthGuard)
export class UsersController {
  constructor(
    private readonly usersService: UsersService,
    private readonly rolePermissionsService: RolePermissionsService,
  ) {}

  // ──────────────────────────────────────────────
  // POST /users — create user (ADMIN only)
  // ──────────────────────────────────────────────

  @Post()
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.addButton')
  async create(@Body() dto: CreateUserDto) {
    return this.usersService.create(dto);
  }

  // ──────────────────────────────────────────────
  // GET /users — list users (ADMIN only, paginated)
  // ──────────────────────────────────────────────

  @Get()
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users')
  async findAll(@Query() pagination: PaginationDto) {
    return this.usersService.findAll(pagination);
  }

  // ──────────────────────────────────────────────
  // GET /users/me — current user profile (any authenticated)
  // ──────────────────────────────────────────────

  @Get('me')
  async getMe(@CurrentUser('id') userId: string) {
    return this.usersService.findOne(userId);
  }

  // ──────────────────────────────────────────────
  // GET /users/permissions — full permission matrix (ADMIN only)
  // ──────────────────────────────────────────────

  @Get('permissions')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.roles')
  async getPermissions() {
    return this.rolePermissionsService.findAll();
  }

  // ──────────────────────────────────────────────
  // PUT /users/permissions — bulk update permissions (ADMIN only)
  // ──────────────────────────────────────────────

  @Put('permissions')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.roles.editPermissions')
  async updatePermissions(@Body() dto: UpdateRolePermissionsDto) {
    return this.rolePermissionsService.bulkUpdate(dto.permissions);
  }

  // ──────────────────────────────────────────────
  // GET /users/permissions/seed — seed default permissions (ADMIN only)
  // ──────────────────────────────────────────────

  @Get('permissions/seed')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.roles')
  async seedPermissions() {
    return this.rolePermissionsService.seedDefaults();
  }

  // ──────────────────────────────────────────────
  // GET /users/permissions/:role — permissions for one role (ADMIN only)
  // ──────────────────────────────────────────────

  @Get('permissions/:role')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.roles')
  async getPermissionsByRole(
    @Param('role', new ParseEnumPipe(UserRole)) role: UserRole,
  ) {
    return this.rolePermissionsService.findByRole(role);
  }

  // ──────────────────────────────────────────────
  // GET /users/:id — get user by id (ADMIN only)
  // ──────────────────────────────────────────────

  @Get(':id')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users')
  async findOne(@Param('id') id: string) {
    return this.usersService.findOne(id);
  }

  // ──────────────────────────────────────────────
  // PATCH /users/:id — update user (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch(':id')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.table.editButton')
  async update(
    @Param('id') id: string,
    @Body() dto: UpdateUserDto,
  ) {
    return this.usersService.update(id, dto);
  }

  // ──────────────────────────────────────────────
  // PATCH /users/:id/role — change role (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch(':id/role')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.table.changeRole')
  async updateRole(
    @Param('id') id: string,
    @Body() dto: UpdateRoleDto,
  ) {
    return this.usersService.updateRole(id, dto.role);
  }

  // ──────────────────────────────────────────────
  // PATCH /users/:id/password — change password (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch(':id/password')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.table.editButton')
  async changePassword(
    @Param('id') id: string,
    @Body() dto: ChangePasswordDto,
  ) {
    return this.usersService.changePassword(id, dto.newPassword);
  }

  // ──────────────────────────────────────────────
  // DELETE /users/:id — deactivate user (ADMIN only)
  // ──────────────────────────────────────────────

  @Delete(':id')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.table.deactivate')
  async deactivate(@Param('id') id: string) {
    return this.usersService.deactivate(id);
  }

  // ──────────────────────────────────────────────
  // PATCH /users/:id/reactivate — reactivate user (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch(':id/reactivate')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('users.table.deactivate')
  async reactivate(@Param('id') id: string) {
    return this.usersService.reactivate(id);
  }
}
