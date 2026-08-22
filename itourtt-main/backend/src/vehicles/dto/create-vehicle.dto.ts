import { IsNotEmpty, IsString, IsOptional, IsIn, IsInt, Min, Max } from 'class-validator';

export class CreateVehicleDto {
  @IsNotEmpty()
  @IsString()
  plateNumber!: string;

  @IsNotEmpty()
  @IsString()
  vehicleTypeId!: string;

  @IsOptional()
  @IsIn(['OWNED', 'RENTED', 'CONTRACTED'])
  ownership?: 'OWNED' | 'RENTED' | 'CONTRACTED';

  @IsOptional()
  @IsString()
  supplierId?: string;

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
