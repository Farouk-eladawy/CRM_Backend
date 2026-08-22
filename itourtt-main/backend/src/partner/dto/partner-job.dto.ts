import {
  IsArray,
  IsEmail,
  IsIn,
  IsInt,
  IsNumber,
  IsOptional,
  IsString,
  Min,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';
import { ALL_SERVICE_TYPES } from '../../common/utils/service-type.util.js';

export class PartnerJobExtraDto {
  @IsOptional()
  @IsString()
  extraId?: string;

  @IsString()
  name!: string;

  @IsInt()
  @Min(1)
  qty!: number;

  @IsNumber()
  @Min(0)
  unitAmount!: number;

  @IsString()
  currency!: string;
}

/**
 * A confirmed B2C booking pushed to iTourTT to create an operational job.
 * B2C owns pricing (total/currency are B2C-computed snapshots — iTourTT does NOT
 * re-price). Zone/airport/hotel/vehicleType ids are iTourTT UUIDs from the B2C mirror.
 */
export class PartnerJobDto {
  @IsString()
  b2cBookingRef!: string; // idempotency key → guest_booking.bookingRef

  @IsIn(ALL_SERVICE_TYPES as unknown as string[])
  serviceType!: string;

  @IsString()
  jobDate!: string; // YYYY-MM-DD

  @IsOptional()
  @IsString()
  pickupTime?: string; // ISO datetime

  @IsString()
  fromZoneId!: string;

  @IsString()
  toZoneId!: string;

  @IsOptional()
  @IsString()
  originAirportId?: string;

  @IsOptional()
  @IsString()
  destinationAirportId?: string;

  @IsOptional()
  @IsString()
  hotelId?: string;

  @IsInt()
  @Min(1)
  paxCount!: number;

  @IsString()
  vehicleTypeId!: string;

  @IsOptional()
  @IsString()
  flightNo?: string;

  @IsOptional()
  @IsString()
  carrier?: string;

  @IsOptional()
  @IsString()
  terminal?: string;

  @IsString()
  guestName!: string;

  @IsEmail()
  guestEmail!: string;

  @IsString()
  guestPhone!: string;

  @IsOptional()
  @IsString()
  guestCountry?: string;

  @IsIn(['ONLINE', 'PAY_ON_ARRIVAL'])
  paymentMethod!: string;

  @IsNumber()
  @Min(0)
  total!: number;

  @IsOptional()
  @IsString()
  currency?: string; // defaults EGP

  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => PartnerJobExtraDto)
  extras?: PartnerJobExtraDto[];

  @IsOptional()
  @IsString()
  notes?: string;

  // Optional precise pickup/dropoff points (Google Places)
  @IsOptional() @IsString() pickupPlaceId?: string;
  @IsOptional() @IsNumber() pickupLat?: number;
  @IsOptional() @IsNumber() pickupLng?: number;
  @IsOptional() @IsString() pickupAddress?: string;
  @IsOptional() @IsString() dropoffPlaceId?: string;
  @IsOptional() @IsNumber() dropoffLat?: number;
  @IsOptional() @IsNumber() dropoffLng?: number;
  @IsOptional() @IsString() dropoffAddress?: string;
}
