import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { UpsertExtraDto } from './dto/upsert-extra.dto.js';
import type { Currency } from '../../generated/prisma/enums.js';

@Injectable()
export class ExtrasService {
  constructor(private readonly prisma: PrismaService) {}

  private readonly allowedInclude = {
    allowedVehicleTypes: {
      include: { vehicleType: { select: { id: true, name: true } } },
    },
  };

  // Admin: full list (active + inactive), ordered for management.
  async findAll() {
    const extras = await this.prisma.b2cExtra.findMany({
      orderBy: [{ sortOrder: 'asc' }, { name: 'asc' }],
      include: this.allowedInclude,
    });
    return extras.map((e) => ({
      ...e,
      allowedVehicleTypeIds: e.allowedVehicleTypes.map((a) => a.vehicleTypeId),
    }));
  }

  /**
   * Curated list of ACTIVE extras for operator selection on a job (dispatch/
   * online). Authenticated but ungated by the 'extras' management permission —
   * replaces the old public /public/extras endpoint after the B2C split.
   */
  async getSelectable() {
    const extras = await this.prisma.b2cExtra.findMany({
      where: { isActive: true },
      orderBy: [{ sortOrder: 'asc' }, { name: 'asc' }],
      include: {
        allowedVehicleTypes: {
          include: { vehicleType: { select: { id: true, name: true } } },
        },
      },
    });
    return extras.map((e) => ({
      id: e.id,
      name: e.name,
      description: e.description,
      price: Number(e.price),
      currency: e.currency,
      imageUrl: e.imageUrl,
      occupiesSeat: e.occupiesSeat,
      allowedVehicleTypeIds: e.allowedVehicleTypes.map((a) => a.vehicleTypeId),
      allowedVehicleTypeNames: e.allowedVehicleTypes.map((a) => a.vehicleType.name),
    }));
  }

  // Public: only active extras for the B2C booking flow.
  async findActive() {
    const extras = await this.prisma.b2cExtra.findMany({
      where: { isActive: true },
      orderBy: [{ sortOrder: 'asc' }, { name: 'asc' }],
      include: this.allowedInclude,
    });
    return extras.map((e) => ({
      id: e.id,
      name: e.name,
      description: e.description,
      price: Number(e.price),
      currency: e.currency,
      imageUrl: e.imageUrl,
      occupiesSeat: e.occupiesSeat,
      allowedVehicleTypeIds: e.allowedVehicleTypes.map((a) => a.vehicleTypeId),
      allowedVehicleTypeNames: e.allowedVehicleTypes.map((a) => a.vehicleType.name),
    }));
  }

  async create(dto: UpsertExtraDto) {
    return this.prisma.b2cExtra.create({
      data: {
        name: dto.name,
        description: dto.description ?? null,
        price: dto.price,
        currency: (dto.currency as Currency) ?? 'EGP',
        imageUrl: dto.imageUrl ?? null,
        isActive: dto.isActive ?? true,
        occupiesSeat: dto.occupiesSeat ?? false,
        sortOrder: dto.sortOrder ?? 0,
        ...(dto.allowedVehicleTypeIds && dto.allowedVehicleTypeIds.length > 0 && {
          allowedVehicleTypes: {
            create: dto.allowedVehicleTypeIds.map((vehicleTypeId) => ({ vehicleTypeId })),
          },
        }),
      },
    });
  }

  async update(id: string, dto: UpsertExtraDto) {
    const existing = await this.prisma.b2cExtra.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException('Extra not found');
    return this.prisma.b2cExtra.update({
      where: { id },
      data: {
        name: dto.name,
        description: dto.description ?? null,
        price: dto.price,
        ...(dto.currency !== undefined && { currency: dto.currency as Currency }),
        ...(dto.imageUrl !== undefined && { imageUrl: dto.imageUrl || null }),
        ...(dto.isActive !== undefined && { isActive: dto.isActive }),
        ...(dto.occupiesSeat !== undefined && { occupiesSeat: dto.occupiesSeat }),
        ...(dto.sortOrder !== undefined && { sortOrder: dto.sortOrder }),
        // Replace the allowed-vehicle-type set when provided.
        ...(dto.allowedVehicleTypeIds !== undefined && {
          allowedVehicleTypes: {
            deleteMany: {},
            create: dto.allowedVehicleTypeIds.map((vehicleTypeId) => ({ vehicleTypeId })),
          },
        }),
      },
    });
  }

  async toggleStatus(id: string) {
    const existing = await this.prisma.b2cExtra.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException('Extra not found');
    return this.prisma.b2cExtra.update({
      where: { id },
      data: { isActive: !existing.isActive },
    });
  }

  async remove(id: string) {
    const existing = await this.prisma.b2cExtra.findUnique({ where: { id } });
    if (!existing) throw new NotFoundException('Extra not found');
    await this.prisma.b2cExtra.delete({ where: { id } });
    return { id };
  }
}
