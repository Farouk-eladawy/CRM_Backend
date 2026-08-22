import type { UserRole } from '../../../generated/prisma/enums.js';

export class AuthUserDto {
  id!: string;
  email!: string;
  phone?: string;
  name!: string;
  role!: UserRole;
  roleId?: string;
  roleSlug?: string;
  repId?: string;
  driverId?: string;
}

export class AuthResponseDto {
  accessToken!: string;
  refreshToken!: string;
  user!: AuthUserDto;
}
