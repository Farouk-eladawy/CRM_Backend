import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import * as admin from 'firebase-admin';

@Injectable()
export class PushNotificationsService {
  private readonly logger = new Logger(PushNotificationsService.name);
  private firebaseApp: admin.app.App | null = null;

  constructor(private readonly prisma: PrismaService) {
    this.initializeFirebase();
  }

  private initializeFirebase() {
    const serviceAccountPath = process.env.FIREBASE_SERVICE_ACCOUNT;
    if (!serviceAccountPath) {
      this.logger.warn(
        'FIREBASE_SERVICE_ACCOUNT env var not set. Push notifications will be silently skipped.',
      );
      return;
    }

    try {
      // Avoid re-initializing if already done (e.g., in tests)
      if (admin.apps.length > 0) {
        this.firebaseApp = admin.apps[0]!;
      } else {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const serviceAccount = require(serviceAccountPath);
        this.firebaseApp = admin.initializeApp({
          credential: admin.credential.cert(serviceAccount),
        });
      }
      this.logger.log('Firebase Admin SDK initialized for push notifications.');
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      this.logger.error(`Failed to initialize Firebase Admin SDK: ${msg}`);
      this.firebaseApp = null;
    }
  }

  /**
   * Send a push notification to all device tokens for a given userId.
   */
  async sendToUser(
    userId: string,
    title: string,
    body: string,
    data?: Record<string, string>,
  ): Promise<void> {
    if (!this.firebaseApp) return;

    const tokens = await this.prisma.deviceToken.findMany({
      where: { userId },
      select: { id: true, token: true },
    });

    if (tokens.length === 0) return;

    const messaging = this.firebaseApp.messaging();

    await Promise.allSettled(
      tokens.map(async ({ id, token }) => {
        try {
          await messaging.send({
            token,
            notification: { title, body },
            data: data ?? {},
          });
        } catch (error: unknown) {
          const code =
            error && typeof error === 'object' && 'code' in error
              ? (error as { code: string }).code
              : '';

          if (
            code === 'messaging/invalid-registration-token' ||
            code === 'messaging/registration-token-not-registered'
          ) {
            this.logger.warn(
              `Removing invalid FCM token (id=${id}) for user ${userId}`,
            );
            await this.prisma.deviceToken
              .delete({ where: { id } })
              .catch(() => {});
          } else {
            const msg = error instanceof Error ? error.message : String(error);
            this.logger.error(
              `Failed to send FCM to token ${id} for user ${userId}: ${msg}`,
            );
          }
        }
      }),
    );
  }

  /**
   * Send a push notification to a driver by resolving their userId.
   */
  async sendToDriver(
    driverId: string,
    title: string,
    body: string,
    data?: Record<string, string>,
  ): Promise<void> {
    const driver = await this.prisma.driver.findUnique({
      where: { id: driverId },
      select: { userId: true },
    });

    if (!driver?.userId) return;

    await this.sendToUser(driver.userId, title, body, data);
  }

  /**
   * Send a push notification to a rep by resolving their userId.
   */
  async sendToRep(
    repId: string,
    title: string,
    body: string,
    data?: Record<string, string>,
  ): Promise<void> {
    const rep = await this.prisma.rep.findUnique({
      where: { id: repId },
      select: { userId: true },
    });

    if (!rep?.userId) return;

    await this.sendToUser(rep.userId, title, body, data);
  }
}
