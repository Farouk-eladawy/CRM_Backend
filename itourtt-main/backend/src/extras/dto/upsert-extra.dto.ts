import {
  IsNotEmpty,
  IsString,
  IsOptional,
  IsNumber,
  Min,
  IsBoolean,
  IsInt,
  IsIn,
  IsArray,
} from 'class-validator';

const CURRENCIES = ['EGP', 'USD', 'EUR', 'GBP', 'SAR'];

export class UpsertExtraDto {
  @IsNotEmpty()
  @IsString()
  name!: string;

  @IsOptional()
  @IsString()
  description?: string;

  @IsNumber()
  @Min(0)
  price!: number;

  @IsOptional()
  @IsIn(CURRENCIES)
  currency?: string;

  @IsOptional()
  @IsString()
  imageUrl?: string;

  @IsOptional()
  @IsBoolean()
  isActive?: boolean;

  @IsOptional()
  @IsBoolean()
  occupiesSeat?: boolean;

  // Vehicle type IDs this extra is restricted to. Empty/omitted = any vehicle.
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  allowedVehicleTypeIds?: string[];

  @IsOptional()
  @IsInt()
  @Min(0)
  sortOrder?: number;
}
