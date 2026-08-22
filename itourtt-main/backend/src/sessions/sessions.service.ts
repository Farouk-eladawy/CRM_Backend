import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service.js';

export interface SessionContext {
  ip?: string | null;
  userAgent?: string | null;
}

/** Best-effort friendly device name from a User-Agent string. */
export function deviceNameFromUA(ua?: string | null): string {
  if (!ua) return 'Unknown device';
  const os =
    /iPhone/i.test(ua) ? 'iPhone' :
    /iPad/i.test(ua) ? 'iPad' :
    /Android/i.test(ua) ? 'Android' :
    /Windows/i.test(ua) ? 'Windows' :
    /Mac OS X|Macintosh/i.test(ua) ? 'macOS' :
    /Linux/i.test(ua) ? 'Linux' : '';
  const browser =
    /Edg\//i.test(ua) ? 'Edge' :
    /OPR\/|Opera/i.test(ua) ? 'Opera' :
    /Chrome\//i.test(ua) ? 'Chrome' :
    /Firefox\//i.test(ua) ? 'Firefox' :
    /Safari\//i.test(ua) ? 'Safari' :
    /okhttp|Dart|Flutter|itour/i.test(ua) ? 'Mobile app' : '';
  return [browser, os].filter(Boolean).join(' · ') || 'Unknown device';
}

@Injectable()
export class SessionsService {
  private readonly idleMs: number;

  constructor(
    private readonly prisma: PrismaService,
    config: ConfigService,
  ) {
    this.idleMs = (Number(config.get('SESSION_IDLE_MINUTES')) || 30) * 60_000;
  }

  /** Record a new device session at login. */
  async start(userId: string, sessionId: string, ctx: SessionContext) {
    await this.prisma.userSession.create({
      data: {
        userId,
        sessionId,
        deviceName: deviceNameFromUA(ctx.userAgent),
        ipAddress: ctx.ip ?? null,
        userAgent: ctx.userAgent ?? null,
      },
    });
  }

  /**
   * The user's currently-active session on another device, if any.
   * Active = not ended AND seen within the idle window. Idle/ended sessions are
   * treated as free so a dead device doesn't lock a rep out forever.
   */
  async findActive(userId: string) {
    const cutoff = new Date(Date.now() - this.idleMs);
    return this.prisma.userSession.findFirst({
      where: { userId, endedAt: null, lastSeenAt: { gte: cutoff } },
      orderBy: { lastSeenAt: 'desc' },
    });
  }

  /** Heartbeat — refresh lastSeenAt (throttled to at most once/60s per session). */
  async touch(sessionId: string) {
    const cutoff = new Date(Date.now() - 60_000);
    await this.prisma.userSession.updateMany({
      where: { sessionId, endedAt: null, lastSeenAt: { lt: cutoff } },
      data: { lastSeenAt: new Date() },
    });
  }

  /** Mark a session ended (on logout). */
  async end(sessionId: string) {
    await this.prisma.userSession.updateMany({
      where: { sessionId, endedAt: null },
      data: { endedAt: new Date() },
    });
  }

  /** Admin: list a user's sessions (most recent first). */
  async listForUser(userId: string) {
    const cutoff = new Date(Date.now() - this.idleMs);
    const rows = await this.prisma.userSession.findMany({
      where: { userId },
      orderBy: { startedAt: 'desc' },
      take: 50,
    });
    return rows.map((s) => ({
      ...s,
      active: s.endedAt === null && s.lastSeenAt >= cutoff,
    }));
  }

  /**
   * Admin force-logout: end the session AND clear the user's live sessionId if it
   * matches, so the token stops validating (JwtStrategy checks sid for REP/DRIVER).
   */
  async forceLogout(userId: string, sessionId: string) {
    await this.end(sessionId);
    await this.prisma.user.updateMany({
      where: { id: userId, sessionId },
      data: { sessionId: null, sessionExpiresAt: null, refreshToken: null },
    });
    return { success: true };
  }

  /**
   * Admin "Clear": force-logout the device AND remove the session row entirely, so
   * a stuck/idle record can never block the user's next login. Works on ended rows
   * too — clearing is the one-click fix for a locked-out rep/driver.
   */
  async clear(userId: string, sessionId: string) {
    await this.forceLogout(userId, sessionId);
    await this.prisma.userSession.deleteMany({ where: { userId, sessionId } });
    return { success: true };
  }

  /** Notify Admin + Dispatch Manager + Online Manager of a blocked rep/driver login. */
  async notifyManagersOfConflict(subject: {
    id: string;
    name: string;
    role: string;
  }, ctx: SessionContext) {
    const managers = await this.prisma.user.findMany({
      where: {
        isActive: true,
        deletedAt: null,
        OR: [
          { role: 'ADMIN' },
          { roleRef: { slug: { in: ['admin', 'dispatch-manager', 'online-manager'] } } },
        ],
      },
      select: { id: true },
    });
    if (managers.length === 0) return;
    const device = deviceNameFromUA(ctx.userAgent);
    await this.prisma.userNotification.createMany({
      data: managers.map((m) => ({
        userId: m.id,
        title: 'Blocked login attempt',
        message: `A new login was blocked for ${subject.name} (${subject.role}) — a session is already active on another device.`,
        metadata: {
          kind: 'REP_LOGIN_CONFLICT',
          subjectUserId: subject.id,
          subjectName: subject.name,
          subjectRole: subject.role,
          ipAddress: ctx.ip ?? null,
          deviceName: device,
        },
      })),
    });
  }
}
