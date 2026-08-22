import { Module } from '@nestjs/common';
import { UsersController } from './users.controller.js';
import { UsersService } from './users.service.js';
import { RolePermissionsService } from './role-permissions.service.js';

@Module({
  controllers: [UsersController],
  providers: [UsersService, RolePermissionsService],
  exports: [UsersService, RolePermissionsService],
})
export class UsersModule {}
