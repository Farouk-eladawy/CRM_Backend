import {
  IsNotEmpty,
  IsOptional,
  IsString,
  IsInt,
  IsEnum,
  Min,
  Max,
} from 'class-validator';

export enum VehicleOwnershipEnum {
  OWNED = 'OWNED',
  RENTED = 'RENTED',
  CONTRACTED = 'CONTRACTED',
}

export class CreateSupplierVehicleDto {
  @IsNotEmpty()
  @IsString()
  plateNumber!: string;

  @IsNotEmpty()
  @IsString()
  vehicleTypeId!: string;

  @IsOptional()
  @IsEnum(VehicleOwnershipEnum)
  ownership?: string;

  @IsOptional()
  @IsString()
  color?: string;

  @IsOptional()
  @IsString()
  carBrand?: string;

  @IsOptional()
  @IsString()
  carModel?: string;

  @IsOptional()
  @IsInt()
  @Min(1900)
  @Max(2100)
  makeYear?: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  luggageCapacity?: number;
}

export class UpdateSupplierVehicleDto {
  @IsOptional()
  @IsString()
  plateNumber?: string;

  @IsOptional()
  @IsString()
  vehicleTypeId?: string;

  @IsOptional()
  @IsEnum(VehicleOwnershipEnum)
  ownership?: string;

  @IsOptional()
  @IsString()
  color?: string;

  @IsOptional()
  @IsString()
  carBrand?: string;

  @IsOptional()
  @IsString()
  carModel?: string;

  @IsOptional()
  @IsInt()
  @Min(1900)
  @Max(2100)
  makeYear?: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  luggageCapacity?: number;
}
