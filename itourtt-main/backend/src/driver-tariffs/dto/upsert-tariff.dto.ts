import { IsNumber, IsOptional, IsString, IsBoolean, Min } from 'class-validator';
import { Type } from 'class-transformer';

export class UpsertTariffDto {
  // From location — exactly one of fromZoneId / fromAirportId must be set
  @IsOptional()
  @IsString()
  fromZoneId?: string;

  @IsOptional()
  @IsString()
  fromAirportId?: string;

  // To location — exactly one of toZoneId / toAirportId must be set
  @IsOptional()
  @IsString()
  toZoneId?: string;

  @IsOptional()
  @IsString()
  toAirportId?: string;

  @IsString()
  vehicleTypeId: string;

  @IsNumber()
  @Min(0)
  @Type(() => Number)
  amount: number;

  @IsOptional()
  @IsString()
  currency?: string;

  @IsOptional()
  @IsString()
  notes?: string;

  @IsOptional()
  @IsBoolean()
  isActive?: boolean;

  @IsOptional()
  @IsString()
  jobServiceTypeId?: string;
}
