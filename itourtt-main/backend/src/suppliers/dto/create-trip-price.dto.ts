import {
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
  IsDateString,
  Min,
} from 'class-validator';

export class CreateTripPriceDto {
  @IsNotEmpty()
  @IsString()
  fromZoneId!: string;

  @IsNotEmpty()
  @IsString()
  toZoneId!: string;

  @IsNotEmpty()
  @IsString()
  vehicleTypeId!: string;

  @IsNotEmpty()
  @IsNumber({ maxDecimalPlaces: 2 })
  @Min(0)
  price!: number;

  @IsOptional()
  @IsString()
  currency?: string;

  @IsNotEmpty()
  @IsDateString()
  effectiveFrom!: string;

  @IsOptional()
  @IsDateString()
  effectiveTo?: string;
}
