import { IsNotEmpty, IsOptional, IsString, IsBoolean } from 'class-validator';

export class AssignJobDto {
  @IsNotEmpty()
  @IsString()
  trafficJobId!: string;

  @IsOptional()
  @IsString()
  vehicleId?: string;

  @IsOptional()
  @IsString()
  driverId?: string;

  @IsOptional()
  @IsString()
  repId?: string;

  @IsOptional()
  @IsString()
  externalDriverName?: string;

  @IsOptional()
  @IsString()
  externalDriverPhone?: string;

  @IsOptional()
  @IsString()
  remarks?: string;

  @IsOptional()
  @IsString()
  supplierId?: string;

  @IsOptional()
  @IsString()
  supplierCarTypeId?: string;

  @IsOptional()
  @IsBoolean()
  allowTypeMismatch?: boolean;
}
