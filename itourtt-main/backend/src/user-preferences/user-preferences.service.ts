import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';

@Injectable()
export class UserPreferencesService {
  constructor(private prisma: PrismaService) {}

  async get(userId: string, key: string): Promise<unknown | null> {
    const pref = await this.prisma.userPreference.findUnique({
      where: { userId_key: { userId, key } },
    });
    return pref?.value ?? null;
  }

  async set(userId: string, key: string, value: unknown): Promise<void> {
    await this.prisma.userPreference.upsert({
      where: { userId_key: { userId, key } },
      update: { value: value as any },
      create: { userId, key, value: value as any },
    });
  }
}
