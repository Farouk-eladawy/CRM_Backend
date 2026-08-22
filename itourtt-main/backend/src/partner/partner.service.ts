import {
  Injectable,
  InternalServerErrorException,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { PublicPricesService } from '../public-prices/public-prices.service.js';
import { GuestBookingsService } from '../guest-bookings/guest-bookings.service.js';
import { UpsertPublicPricesDto } from '../public-prices/dto/upsert-public-prices.dto.js';
import { PartnerJobDto } from './dto/partner-job.dto.js';
import { ALL_SERVICE_TYPES } from '../common/utils/service-type.util.js';

const SERVICE_TYPES = [...ALL_SERVICE_TYPES];

@Injectable()
export class PartnerService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly publicPricesService: PublicPricesService,
    private readonly guestBookingsService: GuestBookingsService,
  ) {}

  /**
   * Reference data the B2C standalone mirrors read-only: location tree (flat),
   * vehicle types, service types. B2C prices + books against these iTourTT ids.
   */
  async getReference() {
    const countries = await this.prisma.country.findMany({
      where: { deletedAt: null },
      include: {
        airports: {
          where: { deletedAt: null },
          include: {
            cities: {
              where: { deletedAt: null },
              include: {
                zones: {
                  where: { deletedAt: null },
                  include: { hotels: { where: { deletedAt: null } } },
                },
              },
            },
          },
        },
      },
    });

    const locations: Array<{
      id: string;
      type: string;
      name: string;
      parentId: string | null;
    }> = [];
    let latest = 0;
    const bump = (d?: Date | null) => {
      if (d && d.getTime() > latest) latest = d.getTime();
    };

    for (const c of countries) {
      locations.push({ id: c.id, type: 'COUNTRY', name: c.name, parentId: null });
      bump(c.updatedAt);
      for (const a of c.airports) {
        locations.push({ id: a.id, type: 'AIRPORT', name: a.name, parentId: c.id });
        bump(a.updatedAt);
        for (const ci of a.cities) {
          locations.push({ id: ci.id, type: 'CITY', name: ci.name, parentId: a.id });
          bump(ci.updatedAt);
          for (const z of ci.zones) {
            locations.push({ id: z.id, type: 'ZONE', name: z.name, parentId: ci.id });
            bump(z.updatedAt);
            for (const h of z.hotels) {
              locations.push({ id: h.id, type: 'HOTEL', name: h.name, parentId: z.id });
              bump(h.updatedAt);
            }
          }
        }
      }
    }

    const vehicleTypeRows = await this.prisma.vehicleType.findMany({
      orderBy: { name: 'asc' },
    });
    const vehicleTypes = vehicleTypeRows.map((v) => {
      bump(v.updatedAt);
      return {
        id: v.id,
        name: v.name,
        capacity: v.seatCapacity,
        luggageCapacity: v.luggageCapacity,
        active: v.isActive,
      };
    });

    return {
      version: latest ? new Date(latest).toISOString() : null,
      locations,
      vehicleTypes,
      serviceTypes: SERVICE_TYPES,
    };
  }

  /** B2C pushes its public price lists; reuse the proven bulk upsert. */
  async pushPricing(dto: UpsertPublicPricesDto) {
    const result = await this.publicPricesService.bulkUpsert(dto);
    return { upserted: dto.items?.length ?? 0, result };
  }

  /**
   * Create an operational job from a confirmed B2C booking. Reuses the existing
   * guest-booking → traffic-job path (sets bookingChannel B2C, maps ARR/DEP
   * origin/dest, links the B2C agent, creates the flight). Idempotent on b2cBookingRef.
   */
  async createJob(dto: PartnerJobDto) {
    const existing = await this.prisma.guestBooking.findUnique({
      where: { bookingRef: dto.b2cBookingRef },
      include: { trafficJob: true },
    });
    if (existing?.trafficJob) {
      return this.jobPayload(existing.trafficJob);
    }

    const systemUser = await this.prisma.user.findFirst({
      where: { role: 'ADMIN', isActive: true },
      select: { id: true },
    });
    if (!systemUser) {
      throw new InternalServerErrorException(
        'No system ADMIN user available to own partner jobs',
      );
    }

    // Reuse an existing booking row (retry after a failed convert) or create one.
    const booking =
      existing ??
      (await this.prisma.guestBooking.create({
        data: {
          bookingRef: dto.b2cBookingRef,
          guestName: dto.guestName,
          guestEmail: dto.guestEmail,
          guestPhone: dto.guestPhone,
          guestCountry: dto.guestCountry ?? null,
          serviceType: dto.serviceType as any,
          jobDate: new Date(dto.jobDate),
          pickupTime: dto.pickupTime ? new Date(dto.pickupTime) : null,
          fromZoneId: dto.fromZoneId,
          toZoneId: dto.toZoneId,
          hotelId: dto.hotelId ?? null,
          originAirportId: dto.originAirportId ?? null,
          destinationAirportId: dto.destinationAirportId ?? null,
          flightNo: dto.flightNo ?? null,
          carrier: dto.carrier ?? null,
          terminal: dto.terminal ?? null,
          paxCount: dto.paxCount,
          vehicleTypeId: dto.vehicleTypeId,
          extras: dto.extras?.length
            ? {
                items: dto.extras.map((e) => ({
                  extraId: e.extraId ?? null,
                  name: e.name,
                  qty: e.qty,
                  unitAmount: e.unitAmount,
                  currency: e.currency,
                })),
              }
            : undefined,
          notes: dto.notes ?? null,
          pickupPlaceId: dto.pickupPlaceId ?? null,
          pickupLat: dto.pickupLat ?? null,
          pickupLng: dto.pickupLng ?? null,
          pickupAddress: dto.pickupAddress ?? null,
          dropoffPlaceId: dto.dropoffPlaceId ?? null,
          dropoffLat: dto.dropoffLat ?? null,
          dropoffLng: dto.dropoffLng ?? null,
          dropoffAddress: dto.dropoffAddress ?? null,
          subtotal: dto.total,
          total: dto.total,
          currency: (dto.currency ?? 'EGP') as any,
          paymentMethod: dto.paymentMethod as any,
          bookingStatus: 'CONFIRMED' as any,
        },
      }));

    const job = await this.guestBookingsService.convertToJob(
      booking.id,
      systemUser.id,
    );
    return this.jobPayload(job);
  }

  /** Status poll for B2C's open bookings, by iTourTT job reference (internalRef). */
  async getJobStatuses(refs: string[]) {
    if (!refs.length) return { jobs: [] };
    const jobs = await this.prisma.trafficJob.findMany({
      where: { internalRef: { in: refs }, deletedAt: null },
      select: {
        internalRef: true,
        status: true,
        updatedAt: true,
      },
    });
    return {
      jobs: jobs.map((j) => ({
        jobRef: j.internalRef,
        status: j.status,
        // ponytail: driver/vehicle enrichment via TrafficAssignment relation deferred
        // until the assignment shape is confirmed; contract allows null.
        driver: null,
        vehicle: null,
        updatedAt: j.updatedAt,
      })),
    };
  }

  private jobPayload(job: { id: string; internalRef: string; status: string }) {
    return {
      jobRef: job.internalRef,
      iTourTTJobId: job.id,
      status: job.status,
    };
  }
}
