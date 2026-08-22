import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { PERMISSIONS_KEY } from '../decorators/permissions.decorator.js';
import { ROLES_KEY } from '../decorators/roles.decorator.js';
import { PrismaService } from '../../prisma/prisma.service.js';
import { getAllPermissionKeys } from '../../permissions/permission-registry.js';

@Injectable()
export class PermissionsGuard implements CanActivate {
  // In-memory cache: userId → { permissions, expiresAt }. Static so every guard
  // instance shares it AND services can invalidate it on role/permission changes.
  private static cache = new Map<
    string,
    { permissions: Set<string>; expiresAt: number }
  >();

  private static CACHE_TTL_MS = 300_000; // 5 minutes

  constructor(
    private reflector: Reflector,
    private prisma: PrismaService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    // 1. Check for @Permissions() decorator
    const requiredPermissions = this.reflector.getAllAndOverride<string[]>(
      PERMISSIONS_KEY,
      [context.getHandler(), context.getClass()],
    );

    // 2. Check for legacy @Roles() decorator
    const requiredRoles = this.reflector.getAllAndOverride<string[]>(
      ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );

    // If neither decorator is present, allow
    if (!requiredPermissions?.length && !requiredRoles?.length) {
      return true;
    }

    const { user } = context.switchToHttp().getRequest();
    if (!user) return false;

    // 3. Load user permissions (with caching)
    const granted = await this.getUserPermissions(user.sub || user.id);

    // 4. If @Permissions is set, check permission keys
    if (requiredPermissions?.length) {
      return requiredPermissions.some((perm) => granted.has(perm));
    }

    // 5. Legacy @Roles fallback: check if user's role slug matches
    if (requiredRoles?.length) {
      const userRole = user.role || '';
      return requiredRoles.some(
        (role) => role === userRole || role === userRole.toUpperCase(),
      );
    }

    return true;
  }

  async getUserPermissions(userId: string): Promise<Set<string>> {
    // Check per-request cache first
    const now = Date.now();
    const cached = PermissionsGuard.cache.get(userId);
    if (cached && cached.expiresAt > now) {
      return cached.permissions;
    }

    // Load from database
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: {
        roleId: true,
        role: true,
        roleRef: {
          select: {
            slug: true,
            isSystem: true,
          },
        },
      },
    });

    if (!user) return new Set();

    // ADMIN system role gets ALL permissions
    if (
      user.roleRef?.slug === 'admin' ||
      (!user.roleId && user.role === 'ADMIN')
    ) {
      const allKeys = new Set(getAllPermissionKeys());
      PermissionsGuard.cache.set(userId, {
        permissions: allKeys,
        expiresAt: now + PermissionsGuard.CACHE_TTL_MS,
      });
      return allKeys;
    }

    // Load granted permission keys for the user's role
    if (user.roleId) {
      const records = await this.prisma.rolePermissionV2.findMany({
        where: { roleId: user.roleId },
        select: { permissionKey: true },
      });
      const permissions = new Set(records.map((r) => r.permissionKey));
      PermissionsGuard.cache.set(userId, {
        permissions,
        expiresAt: now + PermissionsGuard.CACHE_TTL_MS,
      });
      return permissions;
    }

    return new Set();
  }

  /**
   * Invalidate cache for a specific user, or all users. Static so services can
   * call it after a role change / permission-grant edit.
   */
  static invalidateCache(userId?: string): void {
    if (userId) {
      PermissionsGuard.cache.delete(userId);
    } else {
      PermissionsGuard.cache.clear();
    }
  }
}
