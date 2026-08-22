import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';

@Injectable()
export class ContactMessagesService {
  constructor(private readonly prisma: PrismaService) {}

  /** Newest first; optionally only unread. */
  async list(unreadOnly = false) {
    return this.prisma.contactMessage.findMany({
      where: unreadOnly ? { isRead: false } : undefined,
      orderBy: { createdAt: 'desc' },
    });
  }

  async unreadCount() {
    const count = await this.prisma.contactMessage.count({
      where: { isRead: false },
    });
    return { count };
  }

  async setRead(id: string, isRead: boolean) {
    const existing = await this.prisma.contactMessage.findUnique({
      where: { id },
    });
    if (!existing) throw new NotFoundException('Message not found.');
    return this.prisma.contactMessage.update({
      where: { id },
      data: { isRead },
    });
  }

  async remove(id: string) {
    const existing = await this.prisma.contactMessage.findUnique({
      where: { id },
    });
    if (!existing) throw new NotFoundException('Message not found.');
    await this.prisma.contactMessage.delete({ where: { id } });
    return { id };
  }
}
