import {
  IsNotEmpty,
  IsString,
  IsInt,
  Min,
  IsOptional,
  IsBoolean,
  IsIn,
} from 'class-validator';

export class CreateVehicleTypeDto {
  @IsNotEmpty()
  @IsString()
  name!: string;

  @IsNotEmpty()
  @IsInt()
  @Min(1)
  seatCapacity!: number;

  @IsOptional()
  @IsString()
  imageUrl?: string;

  @IsOptional()
  @IsString()
  description?: string;

  // ─── B2C display amenities ───────────────────────────────
  @IsOptional()
  @IsBoolean()
  wifi?: boolean;

  @IsOptional()
  @IsBoolean()
  airConditioning?: boolean;

  @IsOptional()
  @IsBoolean()
  gpsTracked?: boolean;

  @IsOptional()
  @IsInt()
  @Min(0)
  luggageCapacity?: number;

  @IsOptional()
  @IsIn(['MANUAL', 'AUTOMATIC'])
  transmission?: 'MANUAL' | 'AUTOMATIC';
}
