import {
  Injectable,
  BadRequestException,
  NotFoundException,
  ForbiddenException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import {
  getAllPermissionKeys,
  getAncestorKeys,
  PERMISSION_REGISTRY,
} from './permission-registry.js';
import type { CreateRoleDto } from './dto/create-role.dto.js';
import type { UpdateRoleDto } from './dto/update-role.dto.js';

@Injectable()
export class PermissionsService {
  constructor(private readonly prisma: PrismaService) {}

  // ─── ROLE CRUD ───

  async createRole(dto: CreateRoleDto) {
    const slug = this.slugify(dto.name);

    const existing = await this.prisma.role.findFirst({
      where: { OR: [{ name: dto.name }, { slug }] },
    });
    if (existing) {
      throw new BadRequestException('A role with this name already exists');
    }

    return this.prisma.role.create({
      data: {
        name: dto.name,
        slug,
        description: dto.description,
        isSystem: false,
      },
    });
  }

  async updateRole(id: string, dto: UpdateRoleDto) {
    const role = await this.prisma.role.findUnique({ where: { id } });
    if (!role) throw new NotFoundException('Role not found');

    const data: Record<string, unknown> = {};
    if (dto.name !== undefined) {
      data.name = dto.name;
      data.slug = this.slugify(dto.name);
    }
    if (dto.description !== undefined) data.description = dto.description;
    if (dto.isActive !== undefined) data.isActive = dto.isActive;

    return this.prisma.role.update({ where: { id }, data });
  }

  async deleteRole(id: string) {
    const role = await this.prisma.role.findUnique({ where: { id } });
    if (!role) throw new NotFoundException('Role not found');
    if (role.isSystem) {
      throw new ForbiddenException('Cannot delete a system role');
    }

    // Check if any users are assigned to this role
    const userCount = await this.prisma.user.count({
      where: { roleId: id },
    });
    if (userCount > 0) {
      throw new BadRequestException(
        `Cannot delete role: ${userCount} user(s) are assigned to it`,
      );
    }

    await this.prisma.$transaction([
      this.prisma.rolePermissionV2.deleteMany({ where: { roleId: id } }),
      this.prisma.role.delete({ where: { id } }),
    ]);
  }

  async findAllRoles() {
    const roles = await this.prisma.role.findMany({
      orderBy: [{ isSystem: 'desc' }, { name: 'asc' }],
      include: {
        _count: { select: { users: true, permissions: true } },
      },
    });
    return roles.map((r) => ({
      id: r.id,
      name: r.name,
      slug: r.slug,
      description: r.description,
      isSystem: r.isSystem,
      isActive: r.isActive,
      userCount: r._count.users,
      permissionCount: r._count.permissions,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
    }));
  }

  async findRoleById(id: string) {
    const role = await this.prisma.role.findUnique({
      where: { id },
      include: {
        permissions: { select: { permissionKey: true } },
        _count: { select: { users: true } },
      },
    });
    if (!role) throw new NotFoundException('Role not found');

    return {
      id: role.id,
      name: role.name,
      slug: role.slug,
      description: role.description,
      isSystem: role.isSystem,
      isActive: role.isActive,
      userCount: role._count.users,
      permissionKeys: role.permissions.map((p) => p.permissionKey),
      createdAt: role.createdAt,
      updatedAt: role.updatedAt,
    };
  }

  // ─── PERMISSION ASSIGNMENT ───

  async setRolePermissions(roleId: string, permissionKeys: string[]) {
    const role = await this.prisma.role.findUnique({ where: { id: roleId } });
    if (!role) throw new NotFoundException('Role not found');

    if (role.slug === 'admin') {
      throw new ForbiddenException(
        'Cannot modify Admin role permissions — Admin always has full access',
      );
    }

    // Validate all keys against registry
    const allValidKeys = new Set(getAllPermissionKeys());
    const invalidKeys = permissionKeys.filter((k) => !allValidKeys.has(k));
    if (invalidKeys.length > 0) {
      throw new BadRequestException(
        `Invalid permission keys: ${invalidKeys.join(', ')}`,
      );
    }

    // Ensure ancestor keys are included (hierarchical rule)
    const fullKeySet = new Set(permissionKeys);
    for (const key of permissionKeys) {
      for (const ancestor of getAncestorKeys(key)) {
        fullKeySet.add(ancestor);
      }
    }

    const keysToInsert = Array.from(fullKeySet);

    // Transaction: delete all existing, insert new
    await this.prisma.$transaction([
      this.prisma.rolePermissionV2.deleteMany({ where: { roleId } }),
      ...keysToInsert.map((permissionKey) =>
        this.prisma.rolePermissionV2.create({
          data: { roleId, permissionKey },
        }),
      ),
    ]);

    // A role's grants changed → drop cached permissions so it takes effect now,
    // not after the 5-minute TTL. Clears all (any user on this role is affected).
    PermissionsGuard.invalidateCache();

    return { roleId, permissionCount: keysToInsert.length };
  }

  // ─── PERMISSION QUERIES ───

  async getUserPermissionKeys(userId: string): Promise<string[]> {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: {
        roleId: true,
        role: true,
        roleRef: { select: { slug: true } },
      },
    });

    if (!user) return [];

    // Admin gets everything
    if (
      user.roleRef?.slug === 'admin' ||
      (!user.roleId && user.role === 'ADMIN')
    ) {
      return getAllPermissionKeys();
    }

    if (!user.roleId) return [];

    const records = await this.prisma.rolePermissionV2.findMany({
      where: { roleId: user.roleId },
      select: { permissionKey: true },
    });

    return records.map((r) => r.permissionKey);
  }

  // ─── REGISTRY ───

  getRegistry() {
    return PERMISSION_REGISTRY;
  }

  // ─── SEED SYSTEM ROLES ───

  async seedSystemRoles() {
    const systemRoles = [
      {
        name: 'Admin',
        slug: 'admin',
        description: 'Full system access',
      },
      {
        name: 'Dispatcher',
        slug: 'dispatcher',
        description: 'Controls traffic jobs and dispatch operations',
      },
      {
        name: 'Accountant',
        slug: 'accountant',
        description: 'Handles finance and financial reports',
      },
      {
        name: 'Agent Manager',
        slug: 'agent-manager',
        description: 'Manages agents, customers, and bookings',
      },
      {
        name: 'Viewer',
        slug: 'viewer',
        description: 'Read-only access to all modules',
      },
      {
        name: 'Rep',
        slug: 'rep',
        description: 'Field representative portal user',
      },
      {
        name: 'Driver',
        slug: 'driver',
        description: 'Driver portal user',
      },
    ];

    const allKeys = getAllPermissionKeys();

    // Page-level keys only (no dots = top-level pages)
    const pageKeys = allKeys.filter((k) => !k.includes('.'));

    for (const roleData of systemRoles) {
      const role = await this.prisma.role.upsert({
        where: { slug: roleData.slug },
        update: { name: roleData.name, description: roleData.description },
        create: { ...roleData, isSystem: true },
      });

      // Skip permission assignment for admin (always has full access in code)
      if (role.slug === 'admin') continue;

      // Determine default permissions for each system role
      let defaultKeys: string[] = [];

      switch (role.slug) {
        case 'dispatcher':
          defaultKeys = allKeys.filter(
            (k) =>
              k.startsWith('dashboard') ||
              k.startsWith('dispatch') ||
              k.startsWith('traffic-jobs') ||
              k.startsWith('vehicles') ||
              k.startsWith('drivers') ||
              k.startsWith('reps') ||
              k.startsWith('locations'),
          );
          break;

        case 'accountant':
          defaultKeys = allKeys.filter(
            (k) =>
              k.startsWith('dashboard') ||
              k.startsWith('finance') ||
              k.startsWith('reports') ||
              k.startsWith('agents') ||
              k.startsWith('customers') ||
              k.startsWith('suppliers'),
          );
          break;

        case 'agent-manager':
          defaultKeys = allKeys.filter(
            (k) =>
              k.startsWith('dashboard') ||
              k.startsWith('agents') ||
              k.startsWith('customers') ||
              k.startsWith('traffic-jobs'),
          );
          break;

        case 'viewer':
          // View-only: page-level access only (no action buttons/forms)
          defaultKeys = pageKeys.filter(
            (k) => k !== 'users' && k !== 'company' && k !== 'whatsapp',
          );
          break;

        case 'rep':
        case 'driver':
          // Portal users: no dashboard permissions
          defaultKeys = [];
          break;
      }

      // Set permissions in bulk
      if (defaultKeys.length > 0) {
        await this.prisma.$transaction([
          this.prisma.rolePermissionV2.deleteMany({
            where: { roleId: role.id },
          }),
          ...defaultKeys.map((permissionKey) =>
            this.prisma.rolePermissionV2.create({
              data: { roleId: role.id, permissionKey },
            }),
          ),
        ]);
      }
    }

    // Assign roleId to existing users based on their legacy role enum
    const roleMap = await this.prisma.role.findMany({
      select: { id: true, slug: true },
    });

    const slugToId = new Map(roleMap.map((r) => [r.slug, r.id]));

    const legacyToSlug: Record<string, string> = {
      ADMIN: 'admin',
      DISPATCHER: 'dispatcher',
      ACCOUNTANT: 'accountant',
      AGENT_MANAGER: 'agent-manager',
      VIEWER: 'viewer',
      REP: 'rep',
      DRIVER: 'driver',
    };

    for (const [legacyRole, slug] of Object.entries(legacyToSlug)) {
      const roleId = slugToId.get(slug);
      if (roleId) {
        await this.prisma.user.updateMany({
          where: { role: legacyRole as any, roleId: null },
          data: { roleId },
        });
      }
    }

    return { message: 'System roles seeded and users migrated successfully' };
  }

  // ─── HELPERS ───

  private slugify(name: string): string {
    return name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }
}
