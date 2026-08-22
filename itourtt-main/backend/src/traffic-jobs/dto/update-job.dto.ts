import {
  IsOptional, IsString, IsDateString, Matches,
  IsInt, IsIn, IsBoolean, IsNumber, Min, ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';
import { FlightInfoDto } from './create-job.dto.js';
import { JobExtraInputDto } from './job-extra-input.dto.js';
import { SELECTABLE_SERVICE_TYPES } from '../../common/utils/service-type.util.js';

export class UpdateJobDto {
  @IsOptional()
  @IsIn(['NEW', 'UPDATED', 'CANCELLED'])
  bookingStatus?: 'NEW' | 'UPDATED' | 'CANCELLED';

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

  @IsOptional()
  @IsIn(SELECTABLE_SERVICE_TYPES as unknown as string[])
  serviceType?: string;

  @IsOptional()
  @IsDateString()
  @Matches(/^[2-9]\d{3}-/, { message: 'jobDate year must be 2000 or later' })
  jobDate?: string;

  @IsOptional()
  @IsInt()
  @Min(1)
  adultCount?: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  childCount?: number;

  @IsOptional()
  @IsString()
  originAirportId?: string;

  @IsOptional()
  @IsString()
  originZoneId?: string;

  @IsOptional()
  @IsString()
  originHotelId?: string;

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

  // Managed extras (catalog-driven). When provided, replaces the job's full extras set.
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
