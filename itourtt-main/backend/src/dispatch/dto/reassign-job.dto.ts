import { IsOptional, IsString, IsBoolean, ValidateIf } from 'class-validator';

export class ReassignJobDto {
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

  /** At least one field must be provided – validated in the service layer. */
  @ValidateIf((o) => !o.vehicleId && !o.driverId && !o.repId && !o.externalDriverName && !o.remarks && !o.supplierCarTypeId)
  _atLeastOne?: never;
}
