import { IsEnum, IsNotEmpty } from 'class-validator';
import { UserRole } from '../../../generated/prisma/enums.js';

export class UpdateRoleDto {
  @IsEnum(UserRole)
  @IsNotEmpty()
  role: UserRole;
}
