import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { UserRole } from '../../generated/prisma/enums.js';
import type { RolePermissionItemDto } from './dto/update-role-permissions.dto.js';

const ALL_MODULES = [
  'dashboard',
  'dispatch',
  'traffic-jobs',
  'finance',
  'reports',
  'locations',
  'vehicles',
  'drivers',
  'reps',
  'agents',
  'suppliers',
  'customers',
] as const;

/** Helper to build a permission row with all flags set to a single value. */
function perm(
  role: UserRole,
  module: string,
  canView: boolean,
  canCreate: boolean,
  canEdit: boolean,
  canDelete: boolean,
) {
  return { role, module, canView, canCreate, canEdit, canDelete };
}

/** Full CRUD access for a role/module combination. */
function fullAccess(role: UserRole, module: string) {
  return perm(role, module, true, true, true, true);
}

/** View-only access for a role/module combination. */
function viewOnly(role: UserRole, module: string) {
  return perm(role, module, true, false, false, false);
}

@Injectable()
export class RolePermissionsService {
  constructor(private readonly prisma: PrismaService) {}

  // ──────────────────────────────────────────────
  // READ – all permissions
  // ──────────────────────────────────────────────

  async findAll() {
    return this.prisma.rolePermission.findMany({
      orderBy: [{ role: 'asc' }, { module: 'asc' }],
    });
  }

  // ──────────────────────────────────────────────
  // READ – permissions for a specific role
  // ──────────────────────────────────────────────

  async findByRole(role: UserRole) {
    return this.prisma.rolePermission.findMany({
      where: { role },
      orderBy: { module: 'asc' },
    });
  }

  // ──────────────────────────────────────────────
  // BULK UPDATE – upsert permissions in a transaction
  // ──────────────────────────────────────────────

  async bulkUpdate(permissions: RolePermissionItemDto[]) {
    const operations = permissions.map((p) =>
      this.prisma.rolePermission.upsert({
        where: {
          role_module: { role: p.role, module: p.module },
        },
        update: {
          canView: p.canView,
          canCreate: p.canCreate,
          canEdit: p.canEdit,
          canDelete: p.canDelete,
        },
        create: {
          role: p.role,
          module: p.module,
          canView: p.canView,
          canCreate: p.canCreate,
          canEdit: p.canEdit,
          canDelete: p.canDelete,
        },
      }),
    );

    return this.prisma.$transaction(operations);
  }

  // ──────────────────────────────────────────────
  // SEED – default permissions for all roles
  // ──────────────────────────────────────────────

  async seedDefaults() {
    const defaults: RolePermissionItemDto[] = [
      // ── ADMIN: full access everywhere ──
      ...ALL_MODULES.map((m) => fullAccess(UserRole.ADMIN, m)),

      // ── DISPATCHER: full on dispatch & traffic-jobs, view on others ──
      ...ALL_MODULES.map((m) => {
        if (m === 'dispatch' || m === 'traffic-jobs') {
          return fullAccess(UserRole.DISPATCHER, m);
        }
        return viewOnly(UserRole.DISPATCHER, m);
      }),

      // ── ACCOUNTANT: full on finance & reports, view on others ──
      ...ALL_MODULES.map((m) => {
        if (m === 'finance' || m === 'reports') {
          return fullAccess(UserRole.ACCOUNTANT, m);
        }
        return viewOnly(UserRole.ACCOUNTANT, m);
      }),

      // ── AGENT_MANAGER: full on agents, customers & traffic-jobs, view on others ──
      ...ALL_MODULES.map((m) => {
        if (m === 'agents' || m === 'customers' || m === 'traffic-jobs') {
          return fullAccess(UserRole.AGENT_MANAGER, m);
        }
        return viewOnly(UserRole.AGENT_MANAGER, m);
      }),

      // ── VIEWER: view-only everywhere ──
      ...ALL_MODULES.map((m) => viewOnly(UserRole.VIEWER, m)),
    ];

    return this.bulkUpdate(defaults);
  }
}
