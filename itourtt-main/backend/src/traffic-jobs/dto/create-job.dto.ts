import {
  IsNotEmpty, IsOptional, IsString, IsDateString, Matches,
  IsInt, IsIn, IsBoolean, IsNumber, Min, ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';
import { JobExtraInputDto } from './job-extra-input.dto.js';
import { SELECTABLE_SERVICE_TYPES } from '../../common/utils/service-type.util.js';

export class FlightInfoDto {
  @IsNotEmpty()
  @IsString()
  flightNo!: string;

  @IsOptional()
  @IsString()
  carrier?: string;

  @IsOptional()
  @IsString()
  terminal?: string;

  @IsOptional()
  @IsDateString()
  arrivalTime?: string;

  @IsOptional()
  @IsDateString()
  departureTime?: string;
}

export class CreateJobDto {
  @IsNotEmpty()
  @IsIn(['ONLINE', 'B2B'])
  bookingChannel!: 'ONLINE' | 'B2B';

  @IsOptional()
  @IsString()
  agentId?: string;

  @IsOptional()
  @IsString()
  agentRef?: string;

  @IsOptional()
  @IsString()
  customerJobId?: string;

  @IsOptional()
  @IsString()
  customerId?: string;

  @IsNotEmpty()
  @IsIn(SELECTABLE_SERVICE_TYPES as unknown as string[])
  serviceType!: string;

  @IsNotEmpty()
  @IsDateString()
  @Matches(/^[2-9]\d{3}-/, { message: 'jobDate year must be 2000 or later' })
  jobDate!: string;

  @IsNotEmpty()
  @IsInt()
  @Min(1)
  adultCount!: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  childCount?: number;

  // Origin – exactly one must be provided
  @IsOptional()
  @IsString()
  originAirportId?: string;

  @IsOptional()
  @IsString()
  originZoneId?: string;

  @IsOptional()
  @IsString()
  originHotelId?: string;

  // Destination – exactly one must be provided
  @IsOptional()
  @IsString()
  destinationAirportId?: string;

  @IsOptional()
  @IsString()
  destinationZoneId?: string;

  @IsOptional()
  @IsString()
  destinationHotelId?: string;

  @IsOptional()
  @IsString()
  clientName?: string;

  @IsOptional()
  @IsString()
  clientMobile?: string;

  // Managed extras (catalog-driven). Replaces the legacy booster/baby/wheelchair fields.
  @IsOptional()
  @ValidateNested({ each: true })
  @Type(() => JobExtraInputDto)
  extras?: JobExtraInputDto[];

  @IsOptional()
  @IsBoolean()
  printSign?: boolean;

  @IsOptional()
  @IsDateString()
  pickUpTime?: string;

  @IsOptional()
  @IsString()
  notes?: string;

  @IsOptional()
  @IsBoolean()
  collectionRequired?: boolean;

  @IsOptional()
  @IsNumber()
  @Min(0.01)
  collectionAmount?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR'])
  collectionCurrency?: string;

  @IsOptional()
  @IsNumber()
  @Min(0.01)
  transferPrice?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  transferPriceCurrency?: string;

  @IsOptional()
  @IsString()
  requestedVehicleTypeId?: string;

  @IsOptional()
  @IsString()
  custRepName?: string;

  @IsOptional()
  @IsString()
  custRepMobile?: string;

  @IsOptional()
  @IsString()
  custRepMeetingPoint?: string;

  @IsOptional()
  @IsDateString()
  custRepMeetingTime?: string;

  @IsOptional()
  @IsNumber()
  @Min(0.01)
  priceAmount?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  priceCurrency?: string;

  @IsOptional()
  @ValidateNested()
  @Type(() => FlightInfoDto)
  flight?: FlightInfoDto;

  @IsOptional()
  @IsString()
  jobServiceTypeId?: string;
}
