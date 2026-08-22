import {
  IsString,
  IsNumber,
  IsOptional,
  IsDateString,
  IsArray,
  ValidateNested,
  Min,
  IsEnum,
} from 'class-validator';
import { Type } from 'class-transformer';

export enum ServiceTypeEnum {
  ARR = 'ARR',
  DEP = 'DEP',
  DAY_TOUR = 'DAY_TOUR',
  ONE_WAY_TRANSFER = 'ONE_WAY_TRANSFER',
  RETURN = 'RETURN',
}

export class PriceItemDto {
  @IsEnum(ServiceTypeEnum)
  serviceType!: string;

  @IsString()
  fromZoneId!: string;

  @IsString()
  toZoneId!: string;

  @IsString()
  vehicleTypeId!: string;

  @IsNumber()
  @Min(0)
  price!: number;

  @IsNumber()
  @Min(0)
  driverTip!: number;

  @IsOptional()
  @IsDateString()
  effectiveFrom?: string;

  @IsOptional()
  @IsDateString()
  effectiveTo?: string;
}

export class BulkPriceListDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => PriceItemDto)
  items!: PriceItemDto[];
}
